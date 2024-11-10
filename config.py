import yaml
from typing import List, Dict
from dataclasses import dataclass

@dataclass
class CategoryConfig:
    id: str
    name: str
    url: str
    description: str

class ConfigLoader:
    def __init__(self, config_path: str = "categories.yaml"):
        self.config_path = config_path
        self.categories: List[CategoryConfig] = []

    def load_config(self) -> List[CategoryConfig]:
        """Load category configurations from YAML file"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)

            self.categories = [
                CategoryConfig(**category)
                for category in config['categories']
            ]
            return self.categories

        except Exception as e:
            print(f"Error loading config: {e}")
            return []

    def get_urls(self) -> List[str]:
        """Get list of URLs from loaded configurations"""
        return [category.url for category in self.categories]

    def get_category_by_id(self, category_id: str) -> CategoryConfig:
        """Get category configuration by ID"""
        for category in self.categories:
            if category.id == category_id:
                return category
        return None
