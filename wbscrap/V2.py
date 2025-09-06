import asyncio
import json
from playwright.async_api import async_playwright

async def scrape_products():
    url = "https://www.ehadish.com/products/category-mobile-sub-mobile/"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True) 
        page = await browser.new_page()
        await page.goto(url, timeout=60000)

        # صبر تا محصولات لود بشن
        await page.wait_for_selector("div.bx-product")

        products_dict = {}

        product_divs = await page.query_selector_all("div.bx-product")
        for product in product_divs:
            title_tag = await product.query_selector("h2 a")
            title = await title_tag.inner_text()
            link = await title_tag.get_attribute("href")

            img_tag = await product.query_selector("div.bx-img img")
            img_src = await img_tag.get_attribute("src")

            price_tag = await product.query_selector("div.bx-price")
            price = (await price_tag.inner_text() if price_tag else "").replace("تومان", "").strip()

            products_dict[title] = {
                "link": f"https://www.ehadish.com{link}",
                "price": price,
                "image": img_src,
            }

        await browser.close()

        # ذخیره در فایل JSON
        with open("products.json", "w", encoding="utf-8") as f:
            json.dump(products_dict, f, ensure_ascii=False, indent=4)

        print("خروجی در فایل products.json ذخیره شد.")

if __name__ == "__main__":
    asyncio.run(scrape_products())
