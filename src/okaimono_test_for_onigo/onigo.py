from typing import Any, Dict, Union, List
from urllib.parse import urljoin

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from playwright.sync_api import Page


LLM = Union[ChatOpenAI, ChatOllama]


class ShoppingList(BaseModel):
    items: List[str] = Field(..., description="買い物のアイテムリスト")


class ItemCategory(BaseModel):
    category_name: str = Field(..., description="商品のカテゴリー名")
    category_path: str = Field(..., description="商品のカテゴリーへのパス")


class OnigoClient:

    BASE = "https://app.onigo.club"

    def __init__(self, llm: LLM, page: Page, email: str, query: str):
        self.llm = llm
        self.page = page
        self.email = email
        self.query = query
        self.cart: List[Dict[str, Any]] = []

    @staticmethod
    def build_url(path: str) -> str:
        return urljoin(OnigoClient.BASE, path)

    def login(self) -> None:
        page_url = self.build_url("shop")
        self.page.goto(page_url)
        self.page.wait_for_timeout(1000)
        if self.page.url.startswith(page_url):
            return
        self.page.get_by_text("ログイン").click()
        self.page.locator("input").fill(self.email)
        self.page.wait_for_timeout(1000)
        self.page.get_by_text("送信").click()
        while True:
            two_fa = input("認証コードを入力してください：")
            if not two_fa:
                continue
            self.page.locator("input").fill(two_fa)
            self.page.get_by_text("ログインする").click()
            self.page.wait_for_timeout(1000)
            if self.page.url.startswith(page_url):
                return

    def get_item_list(self) -> List[str]:
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "あなたはお買い物アシスタントです。ユーザのクエリからお買い物すべき商品のリストを作ります。",
                ),
                ("human", "{query}"),
            ]
        )
        chain = prompt | self.llm.with_structured_output(ShoppingList)
        shopping_list = chain.invoke({"query": self.query})
        return shopping_list.items

    def get_item_category(self, item: str) -> ItemCategory:
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """
                    あなたはお買い物アシスタントです。ユーザーが探している食材からカテゴリーのパスを返してください。\n\n
                    カテゴリー：{{"categories":[
                        {{"category":"果物・野菜","path":"shop#果物・野菜"}},
                        {{"category":"お肉・餃子の皮類","path":"shop#お肉・餃子の皮類"}},
                        {{"category":"ハム・ソーセージ・肉加工品","path":"shop#ハム・ソーセージ・肉加工品"}},
                        {{"category":"お魚","path":"shop#お魚"}},
                        {{"category":"卵・牛乳・乳製品","path":"shop#卵・牛乳・乳製品"}},
                        {{"category":"豆腐・納豆・蒟蒻・練物・漬物","path":"shop#豆腐・納豆・蒟蒻・練物・漬物"}},
                        {{"category":"時短おかず・弁当・寿司・惣菜","path":"shop#時短おかず・弁当・寿司・惣菜"}},
                        {{"category":"お菓子・デザート・アイス","path":"shop#お菓子・デザート・アイス"}},
                        {{"category":"お米・麺・パスタ","path":"shop#お米・麺・パスタ"}},
                        {{"category":"パン・ジャム・蜂蜜・シリアル","path":"shop#パン・ジャム・蜂蜜・シリアル"}},
                        {{"category":"冷凍食品・氷","path":"shop#冷凍食品・氷"}},
                        {{"category":"調味料・油・だし","path":"shop#調味料・油・だし"}},
                        {{"category":"レトルト・ルー・スープ","path":"shop#レトルト・ルー・スープ"}},
                        {{"category":"缶詰・乾物・粉類","path":"shop#缶詰・乾物・粉類"}},
                        {{"category":"飲料・お水","path":"shop#飲料・お水"}},
                        {{"category":"お酒","path":"shop#お酒"}},
                        {{"category":"日用品・美容","path":"shop#日用品・美容"}},
                        {{"category":"ベビー・ペット","path":"shop#ベビー・ペット"}}
                    ]}}
                    """,
                ),
                ("human", "商品：{item}"),
            ]
        )
        chain = prompt | self.llm.with_structured_output(ItemCategory)
        item_cat = chain.invoke({"item": item})
        return item_cat

    def go_to_home(self):
        self.page.goto(self.build_url("shop"))

    def run(self):
        self.login()
        items = self.get_item_list()
        for item in items:
            cat = self.get_item_category(item)
            print(item, cat)
            if cat is not None:
                self.page.goto(self.build_url(cat.category_path))
                self.page.wait_for_timeout(1000)
                self.go_to_home()
                self.page.wait_for_timeout(1000)
