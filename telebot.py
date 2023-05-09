# Importing all needed modules.
import time
import requests
from cerber import SecurityManager


class TelegramBot:
    def __init__(self, telegram_token : str, gateway_token : str, gateway_endpoint : str, timeout : int = 10) -> None:
        '''
            The constructor of the TelegramBot.
                :param telegram_token: str
                    The authentication token for the using Telegram API.
                :param gateway_token: str
                    The authentication token for the Gateway.
                :param gateway_endpoint: str
                    The endpoint to send all messages to the Gateway.
        '''
        self.telegram_token = telegram_token
        self.gateway_security_manager = SecurityManager(gateway_token)
        self.timeout = timeout
        self.offset = None

        self.base_url = f"https://api.telegram.org/bot{self.telegram_token}"
        self.get_messages_url = self.base_url + "/getUpdates?timeout=100&offset={}"
        self.send_message_url = self.base_url + "/sendMessage?chat_id={}&text={}"
        self.gateway_endpoint = gateway_endpoint

    def get_messages(self) -> None:
        '''
            This function gets all new messages from the Telegram API.
        '''
        # Getting new messages from the Telegram API.
        telegram_response = requests.get(
            self.get_messages_url.format(self.offset)
        ).json()

        # Checking if there are messages.
        if "ok" in telegram_response:
            if telegram_response["ok"]:
                msgs = telegram_response["result"]
                messages = []
                if msgs:

                    # Iterating through all messages and extracting it's text.
                    for item in msgs:
                        self.offset = item["update_id"] + 1
                        try:
                            text = item["message"]["text"]
                        except:
                            text = None
                        if text:
                            # Adding the response information to the list of messages.
                            messages.append(
                                {
                                    "text" : text,
                                    "telegram_user_id" : item["message"]["from"]["id"],
                                    "is_bot" : item["message"]["from"]["is_bot"],
                                    "first_name" : item["message"]["from"]["first_name"],
                                    "last_name" : item["message"]["from"]["last_name"],
                                    "username" : item["message"]["from"]["username"],
                                    "chat_id" : item["message"]["chat"]["id"],
                                    "chat_type" : item["message"]["chat"]["type"],
                                    "date" : item["message"]["date"]
                                }
                            )
                    return messages

    def send_message(self, text : str, chat_id : int) -> None:
        '''
            This function send a text as a message into a chat.
                :param text: str
                    The text of the message to be sent.
                :param chat_id: int
                    The id of the chat to send the message.
        '''
        requests.get(
            self.send_message_url.format(chat_id, text)
        )

    def forward_messages(self, messages : list) -> None:
        '''
            This function forwards the message to the gateway one by one.
                :param messages: list
                    The list of messages to forward to the gateway.
        '''
        for msg in messages:
            # Computing the HMAC of the request to the Gateway.
            hmac = self.gateway_security_manager._SecurityManager__encode_hmac(msg)

            # Sending the request to the Gateway.
            requests.post(self.gateway_endpoint,
                          json=msg,
                          headers = {"Token" : hmac})

    def run(self) -> None:
        '''
            This function is constantly running the logic of the Telegram Interface.
        '''
        while True:
            # Taking a short break to gather messages.
            time.sleep(self.timeout)

            # Getting all new messages.
            messages = self.get_messages()

            # Forwarding messages to the Gateway.
            self.forward_messages(messages)