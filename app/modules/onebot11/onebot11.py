import re
from typing import Optional, List
from threading import Event

from fastapi import WebSocket

from app.api.onebot11 import onebot11_websocket, get_ob11_websocket, stop_ob11_websocket
from app.core.config import settings
from app.core.context import MediaInfo, Context
from app.core.metainfo import MetaInfo
from app.log import logger
from app.utils.common import retry
from app.utils.string import StringUtils


class Onebot11:
    _ds_url = f"http://127.0.0.1:{settings.PORT}/api/v1/message?token={settings.API_TOKEN}"
    _event = Event()

    def __init__(self, OB11_USERS, OB11_GROUPS, **kwargs):
        """
        初始化参数
        """
        self._onebot11_users = OB11_USERS
        self._onebot11_groups = OB11_GROUPS
        self.name = kwargs.get('name')

    @staticmethod
    def get_state() -> bool:
        """
        获取状态
        """
        return get_ob11_websocket()

    async def send_msg(self, title: str, text: str = "", image: str = "",
                       userid: str = "", link: str = None) -> Optional[bool]:
        """
        发送Onebot11消息
        :param title: 消息标题
        :param text: 消息内容
        :param image: 消息图片地址
        :param userid: 用户ID，如有则只发消息给该用户
        :param link: 跳转链接
        :userid: 发送消息的目标用户ID，为空则发给管理员
        """
        if not get_ob11_websocket():
            return False

        if not title and not text:
            logger.warn("标题和内容不能同时为空")
            return False

        try:
            caption = ""
            if image:
                caption = f"[CQ:image,url={image}]"

            if text:
                caption = f"{caption}\n{title}\n{text}"
            else:
                caption = f"{caption}\n{title}"

            if link:
                caption = f"{caption}\n{link}"

            if userid:
                user_id = userid
                group_id = None
            else:
                user_id = self._onebot11_users
                group_id = self._onebot11_groups

            return await self.__send_request(userid=user_id, groupid=group_id if group_id else None, caption=caption)

        except Exception as msg_e:
            logger.error(f"发送消息失败：{msg_e}")
            return False

    async def send_medias_msg(self, medias: List[MediaInfo], userid: str = "",
                              title: str = "", link: str = None) -> Optional[bool]:
        """
        发送媒体列表消息
        """
        if not get_ob11_websocket():
            return None

        try:
            index, image, caption = 1, "", f"*{title}*"
            for media in medias:
                if not image:
                    image = media.get_message_image()

                caption = f"""{caption}
{index}.[media.title_year]
类型：{media.type.value}
评分：{media.vote_average}"""
                if media.vote_average:
                    caption += f"\n评分：{media.vote_average}"

                index += 1
            if link:
                caption += link

            if userid:
                user_id = userid
                group_id = None
            else:
                user_id = self._onebot11_users
                group_id = self._onebot11_groups

            return await self.__send_request(userid=user_id, groupid=group_id if group_id else None, caption=caption)

        except Exception as msg_e:
            logger.error(f"发送消息失败：{msg_e}")
            return False

    async def send_torrents_msg(self, torrents: List[Context],
                                userid: str = "", title: str = "", link: str = None) -> Optional[bool]:
        """
        发送列表消息
        """
        if not get_ob11_websocket():
            return None

        if not torrents:
            return False

        try:
            index, caption = 1, "*%s*" % title
            mediainfo = torrents[0].media_info
            for context in torrents:
                torrent = context.torrent_info
                site_name = torrent.site_name
                meta = MetaInfo(torrent.title, torrent.description)
                link = torrent.page_url
                title = f"{meta.season_episode} " \
                        f"{meta.resource_term} " \
                        f"{meta.video_term} " \
                        f"{meta.release_group}"
                title = re.sub(r"\s+", " ", title).strip()
                free = torrent.volume_factor
                seeder = f"{torrent.seeders}↑"
                caption = f"{caption}\n{index}.【{site_name}】[{title}]({link}) " \
                          f"{StringUtils.str_filesize(torrent.size)} {free} {seeder}"
                index += 1

            if link:
                caption += link

            if userid:
                user_id = userid
                group_id = None
            else:
                user_id = self._onebot11_users
                group_id = self._onebot11_groups

            return await self.__send_request(userid=user_id, groupid=group_id if group_id else None, caption=caption)

        except Exception as msg_e:
            logger.error(f"发送消息失败：{msg_e}")
            return False

    @retry(Exception, logger=logger)
    async def __send_request(self, userid: str | List = None, groupid: str | List = None, caption="") -> bool:
        """
        向Onebot11发送报文
        """
        if isinstance(userid, List):
            for _id in userid:
                await self.__send_private_message(userid=_id, msg=caption)
        else:
            await self.__send_private_message(userid=userid, msg=caption)
            await self.__send_group_message(group_id=userid, msg=caption)
        if isinstance(groupid, List):
            for _id in userid:
                await self.__send_group_message(group_id=_id, msg=caption)
        else:
            await self.__send_group_message(group_id=groupid, msg=caption)
        return True

    async def __send_private_message(self, userid: str, msg: str = ""):
        await get_ob11_websocket().send_json({
            "action": "send_private_msg",
            "params": {
                "user_id": userid,
                "message": msg
            },
            "echo": "123"
        })

    async def __send_group_message(self, group_id: str, msg: str = ""):
        await get_ob11_websocket().send_json({
            "action": "send_group_msg",
            "params": {
                "user_id": group_id,
                "message": msg
            },
            "echo": "123"
        })

    def stop(self):
        """
        停止Onebot11消息接收服务
        """
        if get_ob11_websocket():
            stop_ob11_websocket()
            logger.info("Onebot11消息接收服务已停止")
