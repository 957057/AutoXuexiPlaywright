from base64 import b64decode
from logging import getLogger
from playwright.async_api import Page, TimeoutError

from autoxuexiplaywright.utils.eventmanager import find_event_by_id
from autoxuexiplaywright.utils.lang import get_lang
from autoxuexiplaywright.utils.misc import to_str, img2shell
from autoxuexiplaywright.utils.storage import get_cache_path
from autoxuexiplaywright.utils.config import Config
from autoxuexiplaywright.defines.core import (
    CHECK_ELEMENT_TIMEOUT_SECS, LOGIN_RETRY_TIMES
)
from autoxuexiplaywright.defines.urls import LOGIN_PAGE
from autoxuexiplaywright.defines.selectors import LoginSelectors
from autoxuexiplaywright.defines.events import EventId

from autoxuexiplaywright import appid


async def login(page: Page) -> None:
    config = Config.get_instance()
    find_event_by_id(EventId.STATUS_UPDATED).invoke(get_lang(
        config.lang, "ui-status-loging-in"))
    await page.bring_to_front()
    await page.goto(LOGIN_PAGE)
    try:
        await page.locator(LoginSelectors.LOGIN_CHECK).wait_for(
            timeout=CHECK_ELEMENT_TIMEOUT_SECS*1000)
    except TimeoutError:
        getLogger(appid).info(get_lang(
            config.lang, "core-info-cookie-login-failed"))
        failed_num = 0
        while True:
            qglogin = page.locator(LoginSelectors.LOGIN_QGLOGIN)
            try:
                await qglogin.scroll_into_view_if_needed()
            except TimeoutError:
                getLogger(appid).error(get_lang(
                    config.lang, "core-err-load-qr-failed"))
                raise RuntimeError()
            locator = qglogin.frame_locator(
                LoginSelectors.LOGIN_IFRAME).locator(LoginSelectors.LOGIN_IMAGE)
            img = b64decode(to_str(
                await locator.get_attribute("src")).split(",")[1])
            with open(get_cache_path("qr.png"), "wb") as writer:
                writer.write(img)
            getLogger(appid).info(get_lang(
                config.lang, "core-info-scan-required"))
            img2shell(img)
            locator = page.locator(LoginSelectors.LOGIN_CHECK)
            try:
                await locator.wait_for()
            except TimeoutError as e:
                if failed_num > LOGIN_RETRY_TIMES:
                    getLogger(appid).error(
                        get_lang(config.lang, "core-err-login-failed-too-many-times"))
                    raise e
                else:
                    failed_num += 1
                    await page.reload()
            else:
                getLogger(appid).info(get_lang(
                    config.lang, "core-info-qr-login-success"))
                break
    else:
        getLogger(appid).info(get_lang(
            config.lang, "core-info-cookie-login-success"))
    await page.close()
    find_event_by_id(
        EventId.QR_UPDATED).invoke("".encode())
    await page.context.storage_state(
        path=get_cache_path("cookies.json"))

__all__ = ["login"]