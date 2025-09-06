import asyncio
import json
from playwright.async_api import async_playwright, TimeoutError, Error

BASE_URL = "https://www.ehadish.com"
MAX_CONCURRENT = 5
semaphore = asyncio.Semaphore(MAX_CONCURRENT)

async def scrape_category(context, category_url, category_name):
    products = []
    page = await context.new_page()
    page_num = 1

    while True:
        url = f"{category_url}?page={page_num}"
        try:
            await page.goto(url, timeout=60000)
            await page.wait_for_selector("div.bx-product", timeout=10000)
        except (TimeoutError, Error):
            print(f"Page too slow: {url}. Skipping to next category.")
            break

        product_divs = await page.query_selector_all("div.bx-product")
        if not product_divs:
            break

        products_in_page = []
        for product in product_divs:
            try:
                title_tag = await product.query_selector("h2 a")
                title = await title_tag.inner_text()
                link = await title_tag.get_attribute("href")

                price_tag = await product.query_selector("div.bx-price")
                price = (await price_tag.inner_text() if price_tag else "").replace("تومان", "").strip()

                if not price:  # محصول موجود نیست
                    continue

                products_in_page.append({
                    "title": title,
                    "link": f"{BASE_URL}{link}",
                    "price": price,
                    "categories": [category_name],
                })
            except Exception as e:
                print(f"Failed to parse a product on {url}: {e}")

        if not products_in_page:
            break

        products.extend(products_in_page)
        page_num += 1

    await page.close()
    return products

async def scrape_category_with_semaphore(context, url, name):
    async with semaphore:
        return await scrape_category(context, url, name)

async def scrape_site():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto(BASE_URL, timeout=60000)

        category_links = await page.query_selector_all("a[href*='/products/category-']")
        categories = []
        for c in category_links:
            href = await c.get_attribute("href")
            text = (await c.inner_text()).strip()
            if href and href.startswith("/products/category"):
                categories.append((f"{BASE_URL}{href}", text))
        await page.close()

        tasks = [scrape_category_with_semaphore(context, url, name) for url, name in categories]
        results = await asyncio.gather(*tasks)

        all_products = []
        product_index = {}
        for products in results:
            for p_item in products:
                link = p_item["link"]
                if link in product_index:
                    idx = product_index[link]
                    for cat in p_item["categories"]:
                        if cat not in all_products[idx]["categories"]:
                            all_products[idx]["categories"].append(cat)
                else:
                    all_products.append(p_item)
                    product_index[link] = len(all_products) - 1

        await browser.close()

        # مستقیم به string JSON تبدیل کن
        json_string = json.dumps(all_products, ensure_ascii=False, indent=4)
        return json_string  # ← خروجی آماده برای ارسال به LLM API

if __name__ == "__main__":
    json_output = asyncio.run(scrape_site())
    print(json_output)  # اینو مستقیم می‌تونی به API بفرستی
