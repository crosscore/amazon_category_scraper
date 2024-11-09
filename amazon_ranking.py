import time
import random
from datetime import datetime
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from tqdm import tqdm
from colorama import init, Fore, Style

class AmazonCategoryScraper:
    def __init__(self):
        self.options = webdriver.ChromeOptions()
        self.options.add_argument('--headless')
        self.options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        self.driver = None
        self.results = []
        self.category_map = {}
        init()  # Initialize color output

    def _simplify_amazon_url(self, url):
        """Convert Amazon URL to a simplified format"""
        try:
            if '/dp/' in url:
                asin = url.split('/dp/')[1][:10]
            elif '/gp/product/' in url:
                asin = url.split('/gp/product/')[1][:10]
            elif '/gp/aw/d/' in url:
                asin = url.split('/gp/aw/d/')[1][:10]
            else:
                return asin if (asin := url.split('/')[-1][:10]) else url

            return f"https://www.amazon.co.jp/dp/{asin}"
        except:
            return url

    def start_driver(self):
        """Initialize Selenium driver"""
        try:
            self.driver = webdriver.Chrome(options=self.options)
            self.driver.implicitly_wait(10)
            print(f"{Fore.GREEN}Browser driver initialized successfully{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Failed to initialize browser driver: {e}{Style.RESET_ALL}")
            raise

    def close_driver(self):
        """Close driver"""
        if self.driver:
            self.driver.quit()
            print(f"{Fore.YELLOW}Browser driver closed{Style.RESET_ALL}")

    def scrape_category_page(self, url):
            """Scrape product information from category page"""
            try:
                print(f"\n{Fore.GREEN}Starting category page retrieval:{Style.RESET_ALL} {url}")
                category_ids = self.extract_category_ids(url)

                self.driver.get(url)
                time.sleep(random.uniform(2.0, 4.0))

                try:
                    wait = WebDriverWait(self.driver, 10)
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.s-result-item[data-asin]")))
                except TimeoutException:
                    print(f"{Fore.RED}Page load timeout{Style.RESET_ALL}")
                    return

                products = self.driver.find_elements(By.CSS_SELECTOR, "div.s-result-item[data-asin]")
                print(f"\n{Fore.YELLOW}Number of products detected:{Style.RESET_ALL} {len(products)}")

                with tqdm(total=len(products), desc="Scanning products", colour="green") as pbar:
                    for product in products:
                        try:
                            asin = product.get_attribute('data-asin')
                            if not asin:
                                continue

                            sales_text = None
                            sales_elems = product.find_elements(By.CSS_SELECTOR, "span.a-size-base.a-color-secondary")
                            for elem in sales_elems:
                                if "点以上購入" in elem.text:
                                    sales_text = elem.text
                                    break

                            if not sales_text:
                                continue

                            title_elem = product.find_element(By.CSS_SELECTOR, "h2 a span")
                            title = title_elem.text.strip()

                            try:
                                price_elem = product.find_element(By.CSS_SELECTOR, "span.a-price-whole")
                                price = int(price_elem.text.replace(',', ''))
                            except (NoSuchElementException, ValueError):
                                price = None

                            sales_number = self._parse_sales_number(sales_text)

                            # Get category names for the path
                            categories = [self.get_category_name(cat_id) for cat_id in category_ids]

                            product_info = {
                                'product_id': asin,
                                'sales': sales_number,
                                'price': price,
                                'category_ids': category_ids,
                                'title': title,
                                'scraped_at': datetime.now(),
                                'category_path': ' > '.join(categories)
                            }

                            self.results.append(product_info)
                            self._print_product_info(product_info)

                        except Exception as e:
                            print(f"\n{Fore.RED}Product processing error: {str(e)}{Style.RESET_ALL}")
                        finally:
                            pbar.update(1)

                print(f"\n{Fore.GREEN}Category page retrieval completed{Style.RESET_ALL}")

            except Exception as e:
                print(f"\n{Fore.RED}Page scraping error: {str(e)}{Style.RESET_ALL}")

    def save_results(self, filename=None):
        """Save results to CSV file"""
        if not filename:
            filename = f"amazon_sales_ranking_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        df = pd.DataFrame(self.results)
        # Reorder columns for CSV output
        columns = ['product_id', 'sales', 'price', 'category_ids', 'title', 'scraped_at']
        df = df[columns]  # This will only output the specified columns in the desired order
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"{Fore.GREEN}Data saved to {filename}{Style.RESET_ALL}")

    def _parse_sales_number(self, sales_text):
        """Convert sales text to number"""
        try:
            # Extract number from "過去1か月で4万点以上購入されました"
            number_text = sales_text.split('で')[1].split('点')[0]
            if '万' in number_text:
                number = float(number_text.replace('万', '')) * 10000
            else:
                number = float(number_text.replace(',', ''))
            return int(number)
        except Exception as e:
            print(f"{Fore.RED}Failed to parse sales number: {sales_text} - {e}{Style.RESET_ALL}")
            return 0

    def _print_product_info(self, product_info):
        """Print product information in a readable format"""
        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}Product Name:{Style.RESET_ALL} {product_info['title']}")
        print(f"{Fore.YELLOW}Product ID:{Style.RESET_ALL} {product_info['product_id']}")
        print(f"{Fore.MAGENTA}Sales:{Style.RESET_ALL} {product_info['sales']:,}+ units")
        if product_info['price']:
            print(f"{Fore.BLUE}Price:{Style.RESET_ALL} ¥{product_info['price']:,}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")

    def get_top_products(self, n=10):
        """Get top N products by sales with formatted output"""
        df = pd.DataFrame(self.results)
        if df.empty:
            return None

        # Get top N products and reset index
        top_products = df.nlargest(n, 'sales')[['product_id', 'sales', 'price', 'title']].reset_index(drop=True)

        # Print formatted results
        print(f"\n{Fore.CYAN}Top {n} Products by Sales:{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")

        for idx, row in top_products.iterrows():
            # Truncate title if longer than 30 characters
            title = row['title'][:37] + '...' if len(row['title']) > 40 else row['title']

            print(f"{Fore.YELLOW}No.{idx+1:02d}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}Title:{Style.RESET_ALL} {title}")
            print(f"{Fore.BLUE}ID:{Style.RESET_ALL} {row['product_id']}, ", end='')
            print(f"{Fore.MAGENTA}Sales:{Style.RESET_ALL} {row['sales']:,}, ", end='')
            if pd.notna(row['price']):
                print(f"{Fore.CYAN}Price:{Style.RESET_ALL} ¥{row['price']:,}")
            else:
                print(f"{Fore.CYAN}Price:{Style.RESET_ALL} N/A")
            print(f"{Fore.CYAN}{'-'*60}{Style.RESET_ALL}")
        return None

    def extract_category_ids(self, url):
        """Extract category IDs from URL"""
        try:
            if 'rh=' in url:
                rh_param = url.split('rh=')[1].split('&')[0]
                category_ids = [cat.split('%3A')[1] for cat in rh_param.split('%2C') if 'n%3A' in cat]
                return category_ids
            return []
        except Exception as e:
            print(f"{Fore.RED}Category ID extraction error: {e}{Style.RESET_ALL}")
            return []

    def get_category_name(self, category_id):
        """Get category name from category ID"""
        return self.category_map.get(category_id, f"Category_{category_id}")

    def get_category_ranking(self, level=None):
        """Create category-wise aggregation"""
        df = pd.DataFrame(self.results)
        if df.empty:
            return pd.DataFrame()

        if level is not None:
            # Aggregation at specific category level
            df['category'] = df['category_ids'].apply(lambda x: x[level] if len(x) > level else None)
        else:
            # Aggregation by full category path
            df['category'] = df['category_path']

        ranking = df.groupby('category').agg({
            'sales': 'sum',
            'product_id': 'count'
        }).sort_values('sales', ascending=False)

        return ranking

def main():
    category_urls = [
        "https://www.amazon.co.jp/s?k=juice&i=food-beverage&rh=n%3A57239051%2Cn%3A71442051%2Cn%3A2422779051",
        # Add other category URLs
    ]

    scraper = AmazonCategoryScraper()
    scraper.start_driver()

    try:
        print(f"\n{Fore.CYAN}Starting scraping...{Style.RESET_ALL}")

        for i, url in enumerate(category_urls, 1):
            print(f"\n{Fore.YELLOW}Processing category {i}/{len(category_urls)}{Style.RESET_ALL}")
            scraper.scrape_category_page(url)
            time.sleep(random.uniform(3.0, 6.0))

        print(f"\n{Fore.GREEN}All categories processed{Style.RESET_ALL}")

        if scraper.results:
            # Display top products with new format
            scraper.get_top_products(10)

            top_level_ranking = scraper.get_category_ranking(level=0)
            print("\nTop-level Category Ranking:")
            print(top_level_ranking)

            detailed_ranking = scraper.get_category_ranking()
            print("\nDetailed Category Ranking:")
            print(detailed_ranking)

            scraper.save_results()
            print(f"\n{Fore.GREEN}Results saved to CSV file{Style.RESET_ALL}")
        else:
            print(f"\n{Fore.RED}No scraping results{Style.RESET_ALL}")

    except Exception as e:
        print(f"\n{Fore.RED}An error occurred: {e}{Style.RESET_ALL}")
    finally:
        scraper.close_driver()
        print(f"\n{Fore.CYAN}Scraping completed{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
