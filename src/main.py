import fire
from langchain_ollama import ChatOllama
from playwright.sync_api import sync_playwright

from okaimono_test_for_onigo.onigo import OnigoClient


def proc(
    query: str,
    base_url: str = "http:localhost:11434",
    email: str = "example@example.com",
):
    llm = ChatOllama(
        model="qwen2.5:14b",
        base_url=base_url,
    )
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        oc = OnigoClient(
            llm=llm,
            page=page,
            email=email,
            query=query,
        )
        oc.run()


def main():
    fire.Fire(proc)


if __name__ == "__main__":
    main()
