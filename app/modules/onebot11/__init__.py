import json
from typing import Optional, Union, List, Tuple, Any, Dict

from app.core.config import settings
from app.core.context import MediaInfo, Context
from app.log import logger
from app.modules import _ModuleBase, _MessageBase
from app.modules.onebot11.onebot11 import Onebot11
from app.schemas import MessageChannel, CommingMessage, Notification


class Onebot11Module(_ModuleBase, _MessageBase[Onebot11]):

    def init_module(self) -> None:
        """
        初始化模块
        """
        super().init_service(service_name=Onebot11.__name__.lower(),
                             service_type=Onebot11)

    @staticmethod
    def get_name() -> str:
        return "Onebot11"

    def stop(self):
        """
        停止模块
        """
        for client in self.get_instances().values():
            client.stop()

    def test(self) -> Optional[Tuple[bool, str]]:
        """
        测试模块连接性
        """
        if not self.get_instances():
            return None
        for name, client in self.get_instances().items():
            state = client.get_state()
            if not state:
                return False, f"Onebot11 {name} 未就续"
        return True, ""

    def init_setting(self) -> Tuple[str, Union[str, bool]]:
        pass

    def message_parser(self, source: str, body: Any, form: Any,
                       args: Any) -> Optional[CommingMessage]:
        """
        解析消息内容，返回字典，注意以下约定值：
        self_id: 机器人ID
        sender.userid: 用户ID
        sender.nickname: 昵称
        message_type: group | private
        message: 消息序列
        raw_message: 原始文本
        :param source: 消息来源
        :param body: 请求体
        :param form: 表单
        :param args: 参数
        :return: 渠道、消息体
        """
        """
            {
                "time": 1728304507,
                "self_id": 100000,
                "post_type": "message",
                "message_type": "group",
                "sub_type": "normal",
                "user_id": 123456,
                "group_id": 123456,
                "message_id": 10003,
                "message": [
                    {
                        "type": "text",
                        "data": {
                            "text": "123"
                        }
                    }
                ],
                "raw_message": "123",
                "font": 0,
                "anonymous": null,
                "sender": {
                    "user_id": 123456,
                    "nickname": "admin",
                    "sex": "unknown",
                    "age": 0,
                    "area": "",
                    "card": "",
                    "role": "owner",
                    "level": "0",
                    "title": ""
                }
            }
        """
        # 获取渠道
        client_config = self.get_config(source)
        if not client_config:
            return None
        client: Onebot11 = self.get_instance(source)
        try:
            message: dict = json.loads(body)
        except Exception as err:
            logger.debug(f"解析Onebot11消息失败：{str(err)}")
            return None
        if message:
            text = message.get("raw_message")
            user_id = message.get("user_id")
            user_name = message.get("sender", {}).get("nickname")
            group_id = message.get("group_id", 0)
            flag = False
            if text:
                logger.info(f"收到来自 {source} 的Onebot11消息：userid={user_id}, username={user_name}, text={text}")
                # 检查权限
                permission_users = client_config.config.get("OB11_PERMISSION")
                user_list = client_config.config.get("OB11_USERS")
                group_list = client_config.config.get("OB11_GROUPS")
                if text.startswith("/"):
                    if permission_users \
                            and str(user_id) not in permission_users.split(','):
                        client.send_msg(title="只有管理员才有权限执行此命令", userid=user_id)
                        return None
                else:
                    if user_list \
                            and str(user_id) not in user_list.split(','):
                        logger.info(f"用户{user_id}不在用户白名单中，无法使用此机器人")
                        client.send_msg(title="你不在用户白名单中，无法使用此机器人", userid=user_id)
                        flag = True
                    elif group_list \
                            and str(group_id) not in group_list.split(','):
                        logger.info(f"群号{group_id}不在群白名单中，无法使用此机器人")
                        flag = True
                    if flag:
                        return

                return CommingMessage(channel=MessageChannel.Onebot11, source=source,
                                      userid=user_id, username=user_name, text=text)
        return None

    def post_message(self, message: Notification) -> None:
        """
        发送消息
        :param message: 消息体
        :return: 成功或失败
        """
        for conf in self.get_configs().values():
            if not self.check_message(message, conf.name):
                continue
            targets = message.targets
            userid = message.userid
            if not userid and targets is not None:
                userid = targets.get('Onebot11_userid')
                if not userid:
                    logger.warn(f"用户没有指定 Onebot11用户ID，消息无法发送")
                    return
            client: Onebot11 = self.get_instance(conf.name)
            if client:
                client.send_msg(title=message.title, text=message.text,
                                image=message.image, userid=userid, link=message.link)

    def post_medias_message(self, message: Notification, medias: List[MediaInfo]) -> None:
        """
        发送媒体信息选择列表
        :param message: 消息体
        :param medias: 媒体列表
        :return: 成功或失败
        """
        for conf in self.get_configs().values():
            if not self.check_message(message, conf.name):
                continue
            client: Onebot11 = self.get_instance(conf.name)
            if client:
                client.send_medias_msg(title=message.title, medias=medias,
                                       userid=message.userid, link=message.link)

    def post_torrents_message(self, message: Notification, torrents: List[Context]) -> None:
        """
        发送种子信息选择列表
        :param message: 消息体
        :param torrents: 种子列表
        :return: 成功或失败
        """
        for conf in self.get_configs().values():
            if not self.check_message(message, conf.name):
                continue
            client: Onebot11 = self.get_instance(conf.name)
            if client:
                client.send_torrents_msg(title=message.title, torrents=torrents,
                                         userid=message.userid, link=message.link)

