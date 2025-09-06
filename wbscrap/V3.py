import asyncio
import json
from playwright.async_api import async_playwright

BASE_URL = "https://www.ehadish.com"

async def scrape_category(page, category_url, category_name):
    products = []
    page_num = 1

    while True:
        url = f"{category_url}?page={page_num}"
        await page.goto(url, timeout=60000)

        try:
            await page.wait_for_selector("div.bx-product", timeout=5000)
        except:
            break  # یعنی محصولی نیست یا صفحه تموم شد

        product_divs = await page.query_selector_all("div.bx-product")
        if not product_divs:
            break

        for product in product_divs:
            title_tag = await product.query_selector("h2 a")
            title = await title_tag.inner_text()
            link = await title_tag.get_attribute("href")

            img_tag = await product.query_selector("div.bx-img img")
            img_src = await img_tag.get_attribute("src") if img_tag else ""

            price_tag = await product.query_selector("div.bx-price")
            price = (await price_tag.inner_text() if price_tag else "").replace("تومان", "").strip()

            products.append({
                "title": title,
                "link": f"{BASE_URL}{link}",
                "price": price,
                "image": img_src,
                "category": category_name,
            })

        page_num += 1

    return products

async def scrape_site():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.goto(BASE_URL, timeout=60000)

        # گرفتن همه دسته‌بندی‌ها
        category_links = await page.query_selector_all("a[href*='/products/category-']")
        categories = []
        for c in category_links:
            href = await c.get_attribute("href")
            text = (await c.inner_text()).strip()
            if href and href.startswith("/products/category"):
                categories.append((f"{BASE_URL}{href}", text))

        all_products = []

        for url, name in categories:
            print(f"در حال اسکرپ دسته: {name} ({url})")
            products = await scrape_category(page, url, name)
            all_products.extend(products)

        await browser.close()

        # ذخیره در JSON
        with open("all_products.json", "w", encoding="utf-8") as f:
            json.dump(all_products, f, ensure_ascii=False, indent=4)

        print("تمام محصولات در فایل all_products.json ذخیره شدند.")

if __name__ == "__main__":
    asyncio.run(scrape_site())
