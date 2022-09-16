# (c) AlenPaulVarghese
# -*- coding: utf-8 -*-

from http.client import BadStatusLine, ResponseNotReady
from pyrogram.types import Message, InputMediaPhoto
from PIL import Image, ImageFont, ImageDraw
from pyppeteer.browser import Browser
from pyppeteer import launch, errors
from plugins.logger import logging  # pylint:disable=import-error
from pyrogram import Client
from zipfile import ZipFile
from typing import Optional
from random import randint
from requests import get
from re import sub
import asyncio
import shutil
import math
import io
import os


EXEC_PATH = os.environ.get("GOOGLE_CHROME_SHIM", None)
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)


class Printer(object):
    def __init__(self, _type: str, _link: str, _pid: int):
        self.resolution = {"width": 800, "height": 600}
        self.PID = _pid
        self.type = _type
        self.link = _link
        self.split = False
        self.fullpage = True
        self.location = "./FILES"
        self.name = "@OMG_info"

    def __str__(self):
        res = f'{self.resolution["width"]}+{self.resolution["height"]}'
        return f"({self.type}|{res}|{self.fullpage})\n```{self.link}```"

    @property
    def arguments_to_print(self) -> dict:
        if self.type == "pdf":
            arguments_for_pdf = {
                "displayHeaderFooter": True,
                "margin": {"bottom": 70, "left": 25, "right": 35, "top": 40},
                "printBackground": True,
            }
            if self.resolution["width"] == 800:
                arguments_for_pdf["format"] = "Letter"
            else:
                arguments_for_pdf = {**arguments_for_pdf, **self.resolution}
            if not self.fullpage:
                arguments_for_pdf["pageRanges"] = "1-2"
            return arguments_for_pdf
        elif self.type == "png" or self.type == "jpeg":
            arguments_for_image = {"type": self.type, "omitBackground": True}
            if self.fullpage:
                arguments_for_image["fullPage"] = True
            return arguments_for_image
        return {}

    @property
    def filename(self) -> str:
        return self.location + self.name + "." + self.type

    async def slugify(self, text: str):
        """function to convert string to a valid file-name."""
        # https://stackoverflow.com/a/295466/13033981
        text = sub(r"[^\w\s-]", "", text.lower())
        self.name = sub(r"[-\s]+", "-", text).strip("-_")

    async def allocate_folder(self, chat_id: int, message_id: int):
        """allocate folder based on chat_id and message_id."""
        if not os.path.isdir("./FILES"):
            LOGGER.debug(
                f"WEB_SCRS:{self.PID} --> ./FILES folder not found >> creating new "
            )
            os.mkdir("./FILES")
        location = f"./FILES/{str(chat_id)}/{str(message_id)}/"
        if not os.path.isdir(location):
            LOGGER.debug(
                f"WEB_SCRS:{self.PID} --> user folder not found >> creating {location}"
            )
            os.makedirs(location)
        self.location = location


# https://stackoverflow.com/questions/25705773/image-cropping-tool-python
async def split_func(location: str, filename: str, _format: str) -> list[str]:
    Image.MAX_IMAGE_PIXELS = None
    # https://coderwall.com/p/ovlnwa/use-python-and-pil-to-slice-an-image-vertically
    location_of_image = []
    img = Image.open(filename)
    width, height = img.size
    upper, left, count, slice_size = 0, 0, 1, 800
    slices = int(math.ceil(height / slice_size))
    for _ in range(slices):
        # if we are at the end, set the lower bound to be the bottom of the image
        if count == slices:
            lower = height
        else:
            lower = int(count * slice_size)
        bbox = (left, upper, width, lower)
        working_slice = img.crop(bbox)
        upper += slice_size
        # saving = the slice
        if "jpeg" in _format:
            location_to_save_slice = f"@Web.ScreenCapture-{str(count)}.jpeg"
        else:
            location_to_save_slice = f"@Web.ScreenCapture-{str(count)}.png"
        working_slice.save(fp=location + location_to_save_slice, format=_format)
        location_of_image.append(location + location_to_save_slice)
        count += 1
        await asyncio.sleep(0.001)
    return location_of_image


# https://stackoverflow.com/a/44946732/13033981
async def zipper(location: str, location_of_image: list[str]) -> str:
    location += "@OMG_info.zip"
    with ZipFile(location, "w") as zipper:
        for per_file in location_of_image:
            zipper.write(per_file)
    return location


async def metrics_graber(url: str) -> io.BytesIO:
    _pid = randint(100, 999)
    printer = Printer("statics", url, _pid)
    title, metrics = await screenshot_driver(printer)
    return await draw(title[:25], metrics)


async def draw(name: str, metrics: dict) -> io.BytesIO:
    # DBSans Font is Licensed Under Open Font License
    r = get(
        "https://github.com/googlefonts/dm-fonts/raw/master/Sans/Exports/DMSans-Bold.ttf",
        allow_redirects=True,
    )
    font = ImageFont.truetype(io.BytesIO(r.content), size=1)
    font_size = 1
    # https://stackoverflow.com/a/4902713/13033981
    while font.getsize(name)[0] < 0.90 * 265:
        font_size += 1
        font = ImageFont.truetype(io.BytesIO(r.content), font_size)
    font_paper = Image.new("RGB", (265, 100), color="white")
    draw = ImageDraw.Draw(font_paper)
    await asyncio.sleep(0.2)
    w, h = font.getsize(name)
    draw.text(((265 - w) / 2, (100 - h) / 2), name, font=font, fill="black")
    main_paper = Image.open(
        io.BytesIO(get("https://telegra.ph/file/a6a7f2e40b5ef8b1e0562.png").content)
    )
    LOGGER.info("WEB_SCRS --> site_metrics >> main paper created")
    await asyncio.sleep(0.2)
    main_paper.paste(font_paper, (800, 460, 1065, 560))
    font_paper.close()
    metrics_paper = "".join([f"{x} :- {y}\n" for x, y in metrics.items()])
    draw = ImageDraw.Draw(main_paper)
    font = ImageFont.truetype(io.BytesIO(r.content), 28)
    draw.multiline_text((1185, 215), metrics_paper, fill="white", font=font, spacing=15)
    LOGGER.info("WEB_SCRS --> site_metrics >> main paper rendered successfully")
    return_object = io.BytesIO()
    main_paper.save(return_object, format="png")
    main_paper.close()
    return_object.name = "@Web_ss_Robot.png"
    return return_object


async def settings_parser(link: str, inline_keyboard: list, PID: int) -> Printer:
    # starting to recognize settings
    split, resolution = False, ""
    for settings in inline_keyboard:
        text = settings[0].text
        if "Format" in text:
            if "PDF" in text:
                _format = "pdf"
            else:
                _format = "png" if "PNG" in text else "jpeg"
        if "Page" in text:
            page_value = True if "Full" in text else False
        if "Split" in text:
            split = True if "Yes" in text else False
        if "resolution" in text:
            resolution = text
        await asyncio.sleep(0.00001)
    LOGGER.debug(f"WEB_SCRS:{PID} --> setting confirmation >> ({_format}|{page_value})")
    printer = Printer(_format, link, PID)
    if resolution:
        if "1280" in resolution:
            printer.resolution = {"width": 1280, "height": 720}
        elif "2560" in resolution:
            printer.resolution = {"width": 2560, "height": 1440}
        elif "640" in resolution:
            printer.resolution = {"width": 640, "height": 480}
    if not page_value:
        printer.fullpage = False
    if split:
        printer.split = True
    return printer


async def launch_chrome(retry=False) -> Browser:
    try:
        browser = await launch(
            headless=True,
            logLevel=50,
            executablePath=EXEC_PATH,
            args=[
                "ignoreHTTPSErrors=True",
                "--no-sandbox",
                "--single-process",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--no-zygote",
            ],
        )
        return browser
    except BadStatusLine:
        if not retry:
            LOGGER.info(
                "WEB_SCRS --> request failed -> Excepted BadStatusLine >> retrying..."
            )
            await asyncio.sleep(1.5)
            return await launch_chrome(True)
        elif retry:
            LOGGER.info(
                "WEB_SCRS --> request failed -> Excepted BadStatusLine >> max retry exceeded"
            )
            raise ResponseNotReady("Soory the site is not responding")


async def screenshot_driver(
    printer: Printer, tasks=[]
) -> Optional[tuple[str, dict]]:  # pylint: disable=unsubscriptable-object
    if len(tasks) != 0:
        LOGGER.info(
            f"WEB_SCRS:{printer.PID} --> browser object >> yielded from existing task list"
        )
        browser = tasks[0]
    else:
        LOGGER.info(
            f"WEB_SCRS:{printer.PID} --> no browser object exists >> creating new"
        )
        try:
            browser = await launch_chrome()
            tasks.append(browser)
        except Exception as e:
            LOGGER.critical(e)
            raise ResponseNotReady(e)
    page = await browser.newPage()
    LOGGER.debug(
        f"WEB_SCRS:{printer.PID} --> created new page object >> now setting viewport"
    )
    await page.setViewport(printer.resolution)
    LOGGER.debug(f"WEB_SCRS:{printer.PID} --> fetching received link")
    try:
        await page.goto(printer.link)
        title = await page.title()
        await printer.slugify(title[:14])
        LOGGER.debug(
            f"WEB_SCRS:{printer.PID} --> link fetched successfully -> set filename({printer.filename}) >> now rendering page"
        )
        if printer.type == "pdf":
            await page.pdf(printer.arguments_to_print, path=printer.filename)
        elif printer.type == "statics":
            LOGGER.debug(
                f"WEB_SCRS:{printer.PID} --> site metrics detected >> now rendering image"
            )
            return (title, await page.metrics())
        else:
            await page.screenshot(printer.arguments_to_print, path=printer.filename)
    except errors.PageError:
        LOGGER.info(
            f"WEB_SCRS:{printer.PID} --> request failed -> Excepted PageError >> invalid link"
        )
        raise ResponseNotReady("Not 🚫 A valid link 😓🤔")
    finally:
        await asyncio.sleep(2)
        LOGGER.debug(
            f"WEB_SCRS:{printer.PID} --> page rendered successfully >> now closing page object"
        )
        await page.close()
        if len(await browser.pages()) == 1:
            LOGGER.info(
                f"WEB_SCRS:{printer.PID} --> no task pending >> closing browser object"
            )
            if browser in tasks:
                tasks.remove(browser)
            await browser.close()
        elif len(await browser.pages()) < 2:
            LOGGER.info(
                f"WEB_SCRS:{printer.PID} --> task pending >> leaving browser intact"
            )


async def primary_task(client: Client, msg: Message) -> None:
    _pid = randint(100, 999)
    link = msg.reply_to_message.text
    LOGGER.debug(f"WEB_SCRS:{_pid} --> new request >> processing settings")
    random_message = await msg.edit(text="<b><i>processing...</b></i>")
    printer = await settings_parser(link, msg.reply_markup.inline_keyboard, _pid)
    asyncio.create_task(printer.allocate_folder(msg.chat.id, msg.message_id))
    # logging the request into a specific group or channel
    try:
        log = int(os.environ["LOG_GROUP"])
        LOGGER.debug(f"WEB_SCRS:{printer.PID} --> LOG GROUP FOUND >> sending log")
        await client.send_message(
            log, f'#WebSS:\n\n@{msg.chat.username} got {printer.__str__()}'
        )
    except Exception as e:
        LOGGER.debug(f"WEB_SCRS:{printer.PID} --> LOGGING FAILED >> {e}")
    await random_message.edit(text="<b><i>rendering.</b></i>")
    try:
        await asyncio.wait_for(screenshot_driver(printer), 30)
        out = printer.filename
    except asyncio.exceptions.TimeoutError:
        await random_message.edit("<b>request timeout</b>")
        LOGGER.debug(f"WEB_SCRS:{printer.PID} --> request failed >> timeout")
        return
    except Exception as e:
        await random_message.edit(f"<b>{e}</b>")
        LOGGER.debug(f"WEB_SCRS:{printer.PID} --> request failed >> {e}")
        return
    await random_message.edit(text="<b><i>rendering..</b></i>")
    if printer.split and printer.fullpage:
        LOGGER.debug(
            f"WEB_SCRS:{printer.PID} --> split setting detected -> spliting images"
        )
        await random_message.edit(text="<b><i>spliting images...</b></i>")
        location_of_image = await split_func(
            printer.location, printer.filename, printer.type
        )
        LOGGER.debug(f"WEB_SCRS:{printer.PID} --> image splited successfully")
        # spliting finished
        if len(location_of_image) > 10:
            LOGGER.debug(
                f"WEB_SCRS:{printer.PID} --> found split pieces more than 10 >> zipping file"
            )
            await random_message.edit(
                text="<b>detected images more than 10\n\n<i>Zipping...</i></b>"
            )
            await asyncio.sleep(0.1)
            # zipping if length is too high
            out = await zipper(printer.location, location_of_image)
            LOGGER.debug(
                f"WEB_SCRS:{printer.PID} --> zipping completed >> sending file"
            )
            #  finished zipping and sending the zipped file as document
        else:
            LOGGER.debug(
                f"WEB_SCRS:{printer.PID} --> sending split pieces as media group"
            )
            await random_message.edit(text="<b><i>uploading...</b></i>")
            location_to_send = []
            for count, image in enumerate(location_of_image, start=1):
                location_to_send.append(
                    InputMediaPhoto(media=image, caption=str(count))
                )
            await asyncio.gather(
                client.send_chat_action(msg.chat.id, "upload_photo"),
                client.send_media_group(
                    media=location_to_send,
                    chat_id=msg.chat.id,
                    disable_notification=True,
                ),
            )
            shutil.rmtree(printer.location)
            LOGGER.debug(
                f"WEB_SCRS:{printer.PID} --> mediagroup send successfully >> request statisfied"
            )
            return
    if not printer.fullpage and not printer.type == "pdf":
        LOGGER.debug(
            f"WEB_SCRS:{printer.PID} --> split setting not found >> sending directly"
        )
        await asyncio.gather(
            random_message.edit(text="<b><i>uploading...</b></i>"),
            client.send_chat_action(msg.chat.id, "upload_photo"),
            client.send_photo(photo=out, chat_id=msg.chat.id),
        )
        LOGGER.info(
            f"WEB_SCRS:{printer.PID} --> photo send successfully >> request statisfied"
        )
    if printer.type == "pdf" or printer.fullpage:
        await asyncio.gather(
            client.send_chat_action(msg.chat.id, "upload_document"),
            client.send_document(document=out, chat_id=msg.chat.id),
        )
        LOGGER.debug(
            f"WEB_SCRS:{printer.PID} --> document send successfully >> request statisfied"
        )
    await random_message.delete()
    shutil.rmtree(printer.location)
