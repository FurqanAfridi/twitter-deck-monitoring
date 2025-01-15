####################################################################################################
# ---------------------------------Twitter Monitoring v1.0-----------------------------------------#
####################################################################################################
import os
import sys
import time
import psutil
import shutil
import openai
import logging
import keyboard
import platform
import pyperclip
import traceback
from seleniumbase import SB
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as ec
from selenium.common.exceptions import NoSuchAttributeException, StaleElementReferenceException, \
    NoSuchElementException, TimeoutException, ElementClickInterceptedException, WebDriverException, \
    ElementNotInteractableException

####################################################################################
# ---------------------------------Settings----------------------------------------#
####################################################################################


# Setting current directory
if getattr(sys, "frozen", False):
    os.chdir(os.path.dirname(os.path.abspath(sys.executable)))
else:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Constants
COMMON_EXCEPTIONS = (NoSuchElementException, TimeoutException,
                     StaleElementReferenceException, ElementClickInterceptedException,
                     WebDriverException, ElementNotInteractableException,
                     NoSuchAttributeException)
TEMP_PROFILES = {
    "WINDOWS": os.path.abspath("TwitterMonitoringProfile"),
    "LINUX": "TwitterMonitoringProfile",
    "DARWIN": os.path.abspath("TwitterMonitoringProfile")
}
CLEAR = "cls" if platform.system().upper() == "WINDOWS" else "clear"
LOGGER = logging.getLogger("twitter_accounts_monitoring")
logging.basicConfig(filename="twitter_accounts_monitoring.txt", filemode="w",
                    format="%(asctime)s ==> %(message)s")
LOGGER.setLevel(logging.DEBUG)


# Required Values
CHATGPT_API = ""
PROMPT = """Execute the below for a Twitter Comment Blueprint:

Mandatory
Do not include the text " in the below in the output

Direct Addressing in Comments:

Use Actual Handles: Directly mention the original poster by including their actual Twitter handle (e.g., @username) in the comment for personalization and direct engagement.

Avoid Placeholder Handles: Do not include generic placeholders like "@originalposter" in the output. Ensure that the use of "@" is specific to actual Twitter handles relevant to the conversation.

---------------------
Twitter Comment Blueprint:

Personalize Comments: Reference tweet content directly to personalize comments, avoiding the use of the poster's handle.

Limit Emojis: Employ a maximum of four emojis, such as 💡 for ideas, 👏 for applause, 🤔 for thoughtful queries, and 📚 for educational points, ensuring not more than one per sentence.

Brevity and Length: Keep comments concise; use the extended character limit beyond 280 characters only to add significant value or to elaborate on complex points.

Emoji Selection: Choose emojis that are relevant and add clarity or emotion to the comment. For instance, use 🌟 to highlight excellence, 🚀 for progress or success, 💬 for discussion, and 🤝 for collaboration.

Incorporate Humor: Integrate subtle humor that is gentle and likely to be universally understood, steering clear of sarcasm or jokes that may be misinterpreted.

Suggest Help or Advice: Offer help or advice by framing it as a suggestion or insight, encouraging an exchange of ideas rather than prescribing a course of action.

------
Mandatory
While up to 10,000 characters are available as a blue twitter account, brevity is still preferred for reader engagement.

Limit emoji usage to four per comment and no more than one per sentence to maintain professionalism.

Personalize the comment by referencing the tweet's content instead of using the poster's handle directly.

Prioritize the most valuable insight or question to keep the comment concise while encouraging dialogue.

Combine a professional tone with a friendly touch to make the comment approachable yet authoritative.

Incorporate minimal and universally understood humor to engage readers without overshadowing the main message.

----------------
Mandatory
Content Guidelines:

Only post 1 comment per tweet
Maintain brevity, with less than 10,000 characters.
Avoid using specific mentions like "@OriginalPoster".
Do not use quotes like ".
Use a maximum of 4 emojis.
Add unique insight or expert perspective.
Relate to a relevant story or anecdote.
Stay on-topic with the original tweet or discussion.
Incorporate personalized elements using the poster's handle.
Pose a question to stimulate further conversation.
Express appreciation for the content.
Share experiences indirectly, suitable for a public audience.
Provide additional thoughts for a retweet.
Suggest relevant hashtags to enhance visibility.
Offer help or advice on the post's topic.

------ Engagement and Tone:

Use a conversational tone, as if talking to a friend.
Avoid jargon and opt for clear, simple language.
Engage comfortably, making the reader feel at ease.
Connect effectively with familiar words and phrases.
Reflect a tone of regular engagement with the topic.

------ Interaction Quality:

Ensure genuine interaction, avoiding promotional content.
Avoid controversy and respect all users.
Proofread for quality, with no spelling or grammatical errors.

------ Emotional and Humorous Engagement:

Utilize emojis to convey emotion appropriately, with no more than one per sentence.
Incorporate appropriate, very little humor.

------ Visibility and Outreach:

Incorporate relevant hashtags and strategic tags for engagement.
Remain neutral and respectful, especially on sensitive topics.
Demonstrate a pattern of regular engagement.

------ Additional Considerations:

Offer a fresh perspective or insight.
Remain concise, within Twitter's character limits.
Add value in the event of a quote retweet.
Be genuine and avoid promotional language.
Come across as approachable with a conversational tone.

Important: Do not write anything extra, just respond with comment content without extra indications.

Here below is the Post:


"""

####################################################################################
# ---------------------------------Browser Handler---------------------------------#
####################################################################################

def get_processes_by_port(port):
    to_return_processes = []
    for process in psutil.process_iter():
        for connection in process.connections():
            if connection.laddr.port == port or (connection.raddr and connection.raddr.port == port):
                to_return_processes.append(process)
    return to_return_processes


def exceptional_handler(func):
    def wrapper(*args, **kwargs):
        retry = kwargs.get("retry", 0)
        max_retries = kwargs.get("max_retries", 2)
        if retry >= max_retries:
            raise Exception("Maximum retries reached!")
        try:
            if "retry" in list(kwargs.keys()):
                kwargs.pop("retry")
            if "max_retries" in list(kwargs.keys()):
                kwargs.pop("max_retries")
            return func(*args, **kwargs)
        except COMMON_EXCEPTIONS:
            time.sleep(5)
            return wrapper(retry=retry + 1, max_retries=max_retries, *args, **kwargs)
    return wrapper


def wait_until(condition_func):
    def wrapper(*args, **kwargs):
        kwargs.get("before_loop", lambda: True)()
        max_attempts = kwargs.get("max_tries", -1)
        dots = 1
        attempt = 0
        not_completed = False
        while True:
            kwargs.get("in_loop_before", lambda: True)()
            if condition_func(*args):
                break
            if max_attempts != -1 and attempt >= max_attempts:
                not_completed = True
                break
            attempt += 1
            print(f"{kwargs.get('message', 'Waiting')}{'.' * dots}", end="\r")
            dots = 1 if dots > 2 else dots + 1
            kwargs.get("in_loop_after", lambda: True)()
            time.sleep(kwargs.get("sleep", 0.5))
            print(" " * 100, end="\r")
        kwargs.get("after_loop", lambda: True)()
        return not not_completed
    return wrapper


class BrowserHandler:
    """Handling Chrome browser."""

    def __init__(self, temp_profile: str = None, port: int = 9222) -> None:
        """Handling Chrome browser startup and all options for browser handling."""
        self.platform = platform.system().upper()
        self.temp_profile = temp_profile if temp_profile is not None \
            else TEMP_PROFILES.get(self.platform, "NamePlaceholderProfile")
        self.driver = None
        self.wait = None
        self.seleniumbase_driver = None
        self.sb_init = None
        self.port = port

    def get_element(self, css_selector: str, by_clickable: bool = False, multiple: bool = False) -> WebElement | list:
        condition = ec.presence_of_element_located if not multiple else ec.presence_of_all_elements_located
        if by_clickable:
            condition = ec.element_to_be_clickable
        return self.wait.until(condition((By.CSS_SELECTOR, css_selector)))

    def find_elements(self, css_selector: str, reference_element=None):
        reference = self.driver if reference_element is None else reference_element
        return reference.find_elements(By.CSS_SELECTOR, css_selector)

    def get_element_by_text(self, text: str, css_selector: str = None, elements=None):
        if elements is None:
            elements = self.get_element(css_selector, multiple=True)
        elements_text = self.get_text(element=elements, multiple=True)
        for element_text in elements_text:
            if text.lower() in element_text.lower():
                return elements[elements_text.index(element_text)]
        return None

    @exceptional_handler
    def write(self, css_selector: str, data: str, enter=False):
        input_el = self.get_element(css_selector, by_clickable=True)
        input_el.clear()
        input_el.send_keys(data)
        if enter:
            input_el.send_keys(Keys.ENTER)

    @exceptional_handler
    def click_element(self, css_selector: str = None, element=None, scroll=True):
        if css_selector is not None:
            element = self.get_element(css_selector, by_clickable=True)
        if scroll:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'})", element)
        time.sleep(1)
        element.click()

    @exceptional_handler
    def get_text(self, css_selector=None, element=None, multiple=False):
        if css_selector is not None:
            element = self.get_element(css_selector, multiple=multiple)
        if not multiple:
            return element.get_property("innerText")
        return [el.get_property("innerText") for el in element]

    @exceptional_handler
    def get_attribute(self, attr, css_selector=None, element=None, multiple=False):
        if css_selector is not None:
            element = self.get_element(css_selector, multiple=multiple)
        if not multiple:
            return element.get_attribute(attr)
        return [el.get_attribute(attr) for el in element]

    def start_chrome(self, headless: bool = False, terminate_by_port: bool = False, **kwargs) -> None:
        """Start Chrome Browser."""
        if terminate_by_port:
            processes = get_processes_by_port(self.port)
            for process in processes:
                process.kill()
        kwargs["chromium_arg"] = f'{kwargs.get("chromium_arg", "")},' \
                                 f'--remote-debugging-port={self.port}'.strip(
                                     ",")
        sb_init = SB(uc=True, headed=not headless,
                     user_data_dir=self.temp_profile,
                     headless=headless, **kwargs
                     )
        self.seleniumbase_driver = sb_init.__enter__()
        self.sb_init = sb_init
        self.driver = self.seleniumbase_driver.driver
        self.wait = WebDriverWait(self.driver, 40)
        self.driver.maximize_window()
        self.driver.set_page_load_timeout(300)

    def exit_iframe(self):
        self.driver.switch_to.default_content()

    @exceptional_handler
    def enter_iframe(self, css_selector: str):
        iframe_element = self.get_element(css_selector)
        self.driver.switch_to.frame(iframe_element)

    def kill_browser(self, delete_profile: bool = True) -> None:
        """Kill browser and delete profile."""
        if not hasattr(self, "driver") or self.driver is None:
            return
        self.driver.quit()
        self.sb_init.__exit__(None, None, None)
        self.driver = None
        time.sleep(5)
        if not delete_profile:
            return
        self.delete_profile()

    def delete_profile(self):
        shutil.rmtree(self.temp_profile)

####################################################################################
# -----------------------------------Monitor---------------------------------------#
####################################################################################


class TwitterMonitor(BrowserHandler):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.start_chrome()
        self.driver.set_window_size(1280, 720)

    def is_logged_in(self):
        wait_until(lambda: ("/login" in self.driver.current_url) or self.find_elements(
            "div[aria-label='Account menu']"))(message="Waiting until Twitter loaded")
        return self.find_elements("div[aria-label='Account menu']")

    @exceptional_handler
    def clean_posts(self, account_ref):
        actions = ActionChains(self.driver)
        actions.move_to_element(self.find_elements("div[data-testid=root]", account_ref)[0])
        actions.perform()
        self.click_element(element=self.find_elements("div[aria-label='Clear posts']", account_ref)[0])

    def monitor(self):
        self.driver.get("https://tweetdeck.twitter.com/")
        if not self.is_logged_in():
            raise Exception("Not Logged In!")
        for account in self.find_elements("section[role=region]:not([aria-labelledby])"):
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'})", account)
            wait_until(lambda: "This column was cleared" in self.get_text(element=account) or
                       self.find_elements("article[data-testid=tweet]", account))(
                           message="Waiting until data loads")
            if (not self.find_elements("article[data-testid=tweet]", account)) or \
                    (not self.find_elements("div[aria-label='Clear posts']", account)):
                continue
            for post in self.find_elements("article[data-testid=tweet]", account)[:1]:
                self.reply(post)
            self.clean_posts(account)

    def reply(self, post):
        post_text = self.get_text(element=self.find_elements("div[data-testid=tweetText]", post)[0])
        post_user = self.get_text(element=self.find_elements("div[data-testid=User-Name] > div:first-child", post)[0])
        reply_text = openai_request(f"{PROMPT}\nPost:\n{post_text}")
        pyperclip.copy(f"{reply_text}\n")
        self.click_element(element=self.find_elements("div[data-testid=reply]", post)[0])
        self.click_element("div[role=textbox]")
        username = self.get_text(element=self.find_elements(".css-901oao.css-1hf3ou5.r-18u37iz.r-37j5jr.r-1wvb978.r-1b43r93.r-16dba41.r-14yzgew.r-bcqeeo.r-qvutc0",post)[0])
        ActionChains(driver=self.driver).send_keys(username+" ").key_down(Keys.CONTROL).send_keys("v").key_up(Keys.CONTROL).perform()
        self.click_element("div[data-testid=tweetButton]")
        wait_until(lambda: self.find_elements("div[role=alert]"))(message="Waiting until commented", sleep=0.2)
        LOGGER.info(f"Commented. User => {post_user}")
        time.sleep(2)

####################################################################################
# -----------------------------------ChatGPT---------------------------------------#
####################################################################################
def openai_request(prompt: str):
    openai.api_key = CHATGPT_API
    response = openai.ChatCompletion.create(
        model='gpt-4',
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content


def close_program():
    global close
    close = True


if __name__ == "__main__":
    automation = TwitterMonitor(port=9223)
    close = False
    keyboard.add_hotkey("alt+q", close_program)
    LOGGER.info("Started Monitoring!")
    while not close:
        try:
            automation.monitor()
            time.sleep(600)
        except:
            traceback.print_exc()
    automation.kill_browser(False)
