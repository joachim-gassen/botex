import logging
import time
from typing import Any

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class WebInteractionHandler:
    def __init__(self) -> None:
        """
        Initializes the WebInteractionHandler by setting up the WebDriver options.
        """
        self.driver_options = self.setup_options()

    def setup_options(self) -> Options:
        """
        Configures the options for the Chrome WebDriver.

        :return: A configured instance of Options for WebDriver.
        """
        options = Options()
        options.add_argument("--headless")
        # Needed to work on codespaces but might be a security risk on
        # untrusted web pages
        options.add_argument("--no-sandbox")
        return options

    def create_driver(self) -> webdriver.Chrome:
        """
        Attempts to create a new instance of Chrome WebDriver with retry logic.

        :return: An instance of Chrome WebDriver.
        :raises Exception: If WebDriver fails to start after multiple attempts.
        """
        for attempt in range(1, 6):  # Retry logic to handle startup failures
            try:
                driver = webdriver.Chrome(options=self.driver_options)
                driver.set_window_size(1920, 1400)
                return driver
            except Exception as e:
                logging.warning(
                    f"Attempt {attempt}: Could not start Chrome. Error: {str(e)}. Trying again..."
                )
                time.sleep(1)
        logging.error("Could not start Chrome after 5 attempts.")
        raise Exception("Failed to start WebDriver after multiple attempts.")

    def scan_page(self, driver: webdriver.Chrome, url: str):
        """
        Navigates to a given URL and scans the page for text, interactive elements, and questions.

        :param driver: An instance of Chrome WebDriver.
        :param url: The URL to scan.
        :return: A dictionary with page data including text, whether it's a wait page, the next button, and any questions.
        """
        driver.get(url)
        text = driver.find_element(By.TAG_NAME, "body").text
        debug_text = driver.find_elements(By.CLASS_NAME, "debug-info")
        if debug_text:
            text = text.replace(debug_text[0].text, "")

        wait_page = bool(driver.find_elements(By.CLASS_NAME, "otree-wait-page__body"))
        next_button = driver.find_elements(By.CLASS_NAME, "otree-btn-next")
        next_button = next_button[0] if next_button else None

        questions = self.extract_questions(driver)
        return {
            "text": text,
            "wait_page": wait_page,
            "next_button": next_button,
            "questions": questions,
        }

    def extract_questions(self, driver: webdriver.Chrome):
        """
        Extracts question elements from the current page using the WebDriver.

        :param driver: An instance of Chrome WebDriver.
        :return: A list of dictionaries representing the questions found on the page.
        """
        # Identify all form fields by id
        question_id = []
        question_type = []
        answer_options = []
        fe = driver.find_elements(By.CLASS_NAME, "controls")
        for i in range(len(fe)):
            el = fe[i].find_elements(By.XPATH, ".//*")
            for j in range(len(el)):
                id = el[j].get_attribute("id")
                if id != "":
                    question_id.append(id)
                    type = el[j].get_attribute("type")
                    if type == "text":
                        if el[j].get_attribute("inputmode") == "decimal":
                            type = "float"
                    if type is None:
                        # this is the case when question is a radio button
                        # and potentially also for other non-standard types
                        type = "radio"
                    question_type.append(type)
                    if type == "radio":
                        # get the answer options
                        options = el[j].find_elements(By.CLASS_NAME, "form-check")
                        answer_options.append([o.text for o in options])
                    elif el[j].get_attribute("class") == "form-select":
                        # get the answer options
                        options = el[j].find_elements(By.TAG_NAME, "option")
                        answer_options.append([o.text for o in options[1:]])
                    else:
                        answer_options.append(
                            "This is a free form question and does not have answer options."
                        )
                    break
        if question_id != []:
            labels = driver.find_elements(By.CLASS_NAME, "col-form-label")
            question_label = [x.text for x in labels]
            questions = [
                {
                    "question_id": id,
                    "question_type": qtype,
                    "question_label": label,
                    "answer_options": answer_options,
                }
                for id, qtype, label, answer_options in zip(
                    question_id,
                    question_type,
                    question_label,
                    answer_options,
                    strict=True,
                )
            ]
        else:
            questions = None

        return questions

    def click_on_element(
        self, driver: webdriver.Chrome, element, timeout: int = 3600
    ) -> None:
        """
        Waits until an element is clickable and performs a click action.

        :param driver: An instance of Chrome WebDriver.
        :param element: The web element to click on.
        :param timeout: Maximum time in seconds to wait for the element to become clickable. Defaults to 3600 seconds.
        """
        WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable(element)
        ).click()

    def set_id_value(
        self,
        driver: webdriver.Chrome,
        id: str,
        value_type: str,
        value: Any,
        timeout: int = 3600,
    ) -> None:
        """
        Sets the value of a web element identified by its ID based on the specified type.

        :param driver: An instance of Chrome WebDriver.
        :param id: The ID attribute of the web element.
        :param value_type: The type of the value to set (e.g., 'text', 'radio').
        :param value: The value to set on the web element.
        :param timeout: Maximum time in seconds to wait for the element to be located. Defaults to 3600 seconds.
        """
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.ID, id))
        )
        if value_type != "radio":
            element.send_keys(value)
        else:
            rb = driver.find_element(By.ID, id)
            resp = rb.find_elements(By.CLASS_NAME, "form-check")
            for r in resp:
                if r.text == value:
                    self.click_on_element(
                        driver, r.find_element(By.CLASS_NAME, "form-check-input")
                    )
                    break

    def wait_next_page(self, driver: webdriver.Chrome, timeout: int = 3600) -> None:
        """
        Waits for the next page to be loaded by checking for the presence of a form.

        :param driver: An instance of Chrome WebDriver.
        :param timeout: Maximum time in seconds to wait for the next page to load. Defaults to 3600 seconds.
        """
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CLASS_NAME, "otree-form"))
        )

    def close_driver(self, driver: webdriver.Chrome) -> None:
        """
        Closes the WebDriver and quits the browser session.

        :param driver: An instance of Chrome WebDriver to be closed.
        """
        driver.close()
        driver.quit()
