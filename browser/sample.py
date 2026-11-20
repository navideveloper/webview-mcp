from browser import Browser, run


def main(browser: Browser) -> None:
    page = browser.open("https://jadval.adu.uz")
    print(page.title)
    print(browser.text)


if __name__ == "__main__":
    run(main)