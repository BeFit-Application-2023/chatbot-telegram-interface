# Importing all needed libraries.
from flask import Flask, request, jsonify
import threading
import requests
import time

# Importing all needed modules.
from telebot import TelegramBot
from config import ConfigManager
from cerber import SecurityManager
from schemas import ChatbotResponseSchema

def send_heartbeats():
    '''
        This function sends heartbeat requests to the service discovery.
    '''
    # Getting the Service discovery hmac for message.
    service_discovery_hmac = service_discovery_security_manager._SecurityManager__encode_hmac({"status_code" : 200})
    while True:
        # Senting the request.
        response = requests.post(
            f"http://{config.service_discovery.host}:{config.service_discovery.port}/heartbeat/{config.general.name}",
            json = {"status_code" : 200},
            headers = {"Token" : service_discovery_hmac}
        )
        # Making a pause of 30 seconds before sending the next request.
        status_code = response.status_code
        time.sleep(30)

# Loading the configuration from the configuration file.
config = ConfigManager("config.ini")

# Creation of the Security Manager.
security_manager = SecurityManager(config.security.secret_key)

# Creation of the chatbot Schema.
chatbot_response_schema = ChatbotResponseSchema()

# Creating the security manager for the service discovery.
service_discovery_security_manager = SecurityManager(config.service_discovery.secret_key)

# Computing the HMAC for Service Discovery registration.
SERVICE_DISCOVERY_HMAC = service_discovery_security_manager._SecurityManager__encode_hmac(
    config.generate_info_for_service_discovery()
)

# Registering to the Service discovery.
while True:
    # Sending the request to the service discovery.
    resp = requests.post(
        f"http://{config.service_discovery.host}:{config.service_discovery.port}/{config.service_discovery.register_endpoint}",
        json = config.generate_info_for_service_discovery(),
        headers={"Token" : SERVICE_DISCOVERY_HMAC}
    )

    # If the request is successful then we are going to request the credentials of the needed services.
    if resp.status_code == 200:
        while True:
            time.sleep(3)
            # Computing the HMAC of the request for the Service Discovery.
            service_discovery_hmac = SecurityManager(config.service_discovery.secret_key)._SecurityManager__encode_hmac(
                {"service_names" : ["gateway"]}
            )
            # Making the request to the Service Discovery to get the credentials of the Gateway,
            res = requests.get(
                f"http://{config.service_discovery.host}:{config.service_discovery.port}/get_services",
                json = {"service_names" : ["gateway"]},
                headers={"Token" : service_discovery_hmac}
            )
            if res.status_code == 200:
                time.sleep(5)
                # Starting the process of sending heartbeats.
                threading.Thread(target=send_heartbeats).start()
                res_json = res.json()

                # Creating the Telegram Bot.
                telegram_bot = TelegramBot(config.telegram.telegram_token,
                                           res_json["gateway"]["security"]["secret_key"], # Add gateway token.
                                           f"http://{res_json['gateway']['general']['host']}:{res_json['gateway']['general']['port']}/msg",
                                           config.telegram.timeout)

                break
        break
    else:
        time.sleep(10)

app = Flask(__name__)

@app.route("/send_response", methods = ["POST"])
def send_response():
    # Checking the access token.
    check_response = security_manager.check_request(request)
    if check_response != "OK":
        return check_response, check_response["code"]
    else:
        # Validating the request.
        chatbot_responce, status_code = chatbot_response_schema.validate_json(request.json)

        if status_code == 400:
            return chatbot_responce, status_code
        else:
            # Sending the message to the user.
            telegram_bot.send_message(chatbot_responce["text"],
                                      chatbot_responce["chat_id"])

            return {
                "message" : "OK",
                "code" : 200
            }, 200

# Running the application and the telegram client.
if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(
        host=config.general.host,
        port=config.general.port)).start()
    threading.Thread(target=telegram_bot.run).start()