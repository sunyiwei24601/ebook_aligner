import requests, uuid, json
from langdetect import detect
from enum import Enum
from pygtrans import Translate
from settings import *

# Add your key and endpoint
KEY = "************"
ENDPOINT = "https://api.cognitive.microsofttranslator.com/"
LOCATION = "eastus"


class TranslatorType(Enum):
    PYGTRANS = 1  # PYGTRANS的翻译API，免费，不太稳定，勉强可用
    AZURE = 2  # AZURE的翻译API，需要自己提供secret key


class Translator:
    """
    翻译器主体，调用api翻译文本，考虑未来支持更多api
    """
    def __init__(self, t=TranslatorType.PYGTRANS):
        path = '/translate'
        self.constructed_url = ENDPOINT + path
        self.t = t
        if self.t == TranslatorType.PYGTRANS:
            self.client = Translate()

    def translate_by_azure_api(self, text, from_l='en', to='zh-Hans'):
        """
        调用AZURE API接口，返回中文翻译
        :param text: 文本内容 
        :param from_l: 源文本语言
        :param to: 目标翻译语言
        :return: 翻译内容字符串
        """
        params = {
            'api-version': '3.0',
            'from': from_l,
            'to': [to]
        }

        headers = {
            'Ocp-Apim-Subscription-Key': KEY,
            'Ocp-Apim-Subscription-Region': LOCATION,
            'Content-type': 'application/json',
            'X-ClientTraceId': str(uuid.uuid4())
        }

        # You can pass more than one object in body.
        body = [{
            'text': text
        }]

        request = requests.post(self.constructed_url, params=params, headers=headers, json=body)
        try:
            response = request.json()
        except Exception as e:
            logger.warning("Translation Error! %s", e)
            return ""
        # print(json.dumps(response, sort_keys=True, ensure_ascii=False, indent=4, separators=(',', ': ')))
        return response[0]['translations'][0]['text']

    def translate(self, text):
        if self.t == TranslatorType.AZURE:
            return self.translate_by_azure_api(text)
        elif self.t == TranslatorType.PYGTRANS:
            return self.translate_by_pygtrans(text)
        else:
            logger.error("UnRecognized Translator Type! %s", self.t)
            return ""

    def translate_by_pygtrans(self, text):
        response = self.client.translate(text)
        try:
            return response.translatedText
        except Exception as e:
            response = response.response
            logger.warning("Translate By Pygtrans ErrorCode: %s Error: %s", response.status_code, e)
            return ""


if __name__ == '__main__':
    print(Translator(t=TranslatorType.PYGTRANS).translate('Hello World!'))
