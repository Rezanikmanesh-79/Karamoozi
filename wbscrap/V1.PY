import requests
from bs4 import BeautifulSoup
import json

def get_web_page():
    url = 'https://www.ehadish.com/'
    r = requests.get(url)
    return r.text

def extract_products(html):
    soup = BeautifulSoup(html, 'html.parser')
    products_dict = {}

    for product_div in soup.find_all('div', class_='bx-product'):
        title_tag = product_div.find('h2').find('a')
        title = title_tag.get_text(strip=True)
        link = title_tag['href']
        img_tag = product_div.find('div', class_='bx-img').find('img')
        img_src = img_tag['src']
        price_tag = product_div.find('div', class_='bx-price')
        price = price_tag.get_text(strip=True).replace('تومان','').strip()

        products_dict[title] = {
            'link': f"www.ehadish.com{link}",
            'price': price,
            'image': img_src
        }

    return products_dict

html = get_web_page()
products = extract_products(html)

# ذخیره در فایل JSON
with open('products.json', 'w', encoding='utf-8') as f:
    json.dump(products, f, ensure_ascii=False, indent=4)

print("خروجی در فایل products.json ذخیره شد.")
