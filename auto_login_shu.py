import requests
import os
import platform
import sys
import time
import logging
from abc import ABC, abstractmethod


class EasyLogger:
    def __init__(self):
        self.logger = logging.getLogger('EasyLogger')
        self.logger.setLevel(logging.DEBUG)  # 设置最低的日志级别
        self.handlers = []

    def add(self, filename):
        # 创建文件处理器
        file_handler = logging.FileHandler(filename, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)  # 设置处理器的日志级别

        # 创建一个格式化器，并设置到处理器
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)

        # 将处理器添加到日志记录器
        self.logger.addHandler(file_handler)
        self.handlers.append(file_handler)

        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)  # 设置处理器的日志级别

        # 创建一个格式化器，并设置到处理器
        console_formatter = self.ColoredFormatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)

        # 将处理器添加到日志记录器
        self.logger.addHandler(console_handler)
        self.handlers.append(console_handler)

    def info(self, message):
        self.logger.info(message)

    def warning(self, message):
        self.logger.warning(message)

    def error(self, message):
        self.logger.error(message)

    def close(self):
        for handler in self.handlers:
            handler.close()
            self.logger.removeHandler(handler)

    class ColoredFormatter(logging.Formatter):
        # ANSI 转义码
        GREEN = "\033[92m"
        YELLOW = "\033[93m"
        RED = "\033[91m"
        RESET = "\033[0m"

        def format(self, record):
            # 定义不同级别的颜色
            if record.levelno == logging.INFO:
                color = self.GREEN
            elif record.levelno == logging.WARNING:
                color = self.YELLOW
            elif record.levelno == logging.ERROR:
                color = self.RED
            else:
                color = self.RESET

            # 格式化日志消息
            original_format = super().format(record)
            colored_format = f"{color}{original_format}{self.RESET}"
            return colored_format


logger = EasyLogger()
logger.add(os.path.join(os.path.dirname(os.path.abspath(__file__)), "log.txt"))


class ProxyBase(ABC):
    @abstractmethod
    def is_proxy_enabled(self):
        """
        检测代理是否开启
        :return: True 表示代理已开启，False 表示代理未开启
        """
        pass

    @abstractmethod
    def set_proxy(self, enable=True, proxy_server="127.0.0.1:7890"):
        """
        设置代理开关
        :param enable: True 开启代理，False 关闭代理
        :param proxy_server: 代理服务器地址（例如 "127.0.0.1:7890"）
        """
        pass


class ProxyWindows(ProxyBase):
    def __init__(self):
        self.REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"

    def is_proxy_enabled(self):
        """
        检测代理是否开启
        :return: True 表示代理已开启，False 表示代理未开启
        """
        try:
            import winreg
            registry_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.REG_PATH)
            proxy_enable, _ = winreg.QueryValueEx(registry_key, "ProxyEnable")
            winreg.CloseKey(registry_key)
            return proxy_enable == 1
        except FileNotFoundError:
            logger.error("Proxy settings not found in registry.")
            return False
        except Exception as e:
            logger.error(f"Error: {e}")
            return False

    def set_proxy(self, enable=True, proxy_server="127.0.0.1:7890"):
        """
        设置代理开关
        :param enable: True 开启代理，False 关闭代理
        :param proxy_server: 代理服务器地址（例如 "127.0.0.1:7890"）
        """
        try:
            import winreg
            registry_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.REG_PATH, 0, winreg.KEY_WRITE)
            winreg.SetValueEx(registry_key, "ProxyEnable", 0, winreg.REG_DWORD, 1 if enable else 0)
            if enable:
                winreg.SetValueEx(registry_key, "ProxyServer", 0, winreg.REG_SZ, proxy_server)
            winreg.CloseKey(registry_key)
            logger.info(f"Proxy {'enabled' if enable else 'disabled'} successfully.")
        except Exception as e:
            logger.error(f"Error: {e}")


class ProxyLinux(ProxyBase):
    """
    NOTE: 未测试
    """
    def __init__(self):
        pass

    def is_proxy_enabled(self):
        """
        检测代理是否开启
        :return: True 表示代理已开启，False 表示代理未开启
        """
        http_proxy = os.getenv('http_proxy')
        https_proxy = os.getenv('https_proxy')
        return http_proxy is not None and https_proxy is not None

    def set_proxy(self, enable=True, proxy_server="127.0.0.1:7890"):
        """
        设置代理开关
        :param enable: True 开启代理，False 关闭代理
        :param proxy_server: 代理服务器地址（例如 "127.0.0.1:7890"）
        """
        try:
            if enable:
                os.environ['http_proxy'] = proxy_server
                os.environ['https_proxy'] = proxy_server
                logger.info(f"Proxy enabled successfully with server {proxy_server}.")
            else:
                os.environ.pop('http_proxy', None)
                os.environ.pop('https_proxy', None)
                logger.info("Proxy disabled successfully.")
        except Exception as e:
            logger.error(f"Error: {e}")


class ProxyUtil:
    @staticmethod
    def is_proxy_enabled():
        """
        检测代理是否开启
        :return: True 表示代理已开启，False 表示代理未开启
        """
        if platform.system() == "Windows":
            proxy = ProxyWindows()
        elif platform.system() == "Linux":
            proxy = ProxyLinux()
        else:
            logger.error("Unsupported operating system.")
            return False
        return proxy.is_proxy_enabled()

    @staticmethod
    def set_proxy(enable=True, proxy_server="127.0.0.1:7890"):
        """
        设置代理开关
        :param enable: True 开启代理，False 关闭代理
        :param proxy_server: 代理服务器地址（例如 "127.0.0.1:7890"）
        """
        if platform.system() == "Windows":
            proxy = ProxyWindows()
        elif platform.system() == "Linux":
            proxy = ProxyLinux()
        else:
            logger.error("Unsupported operating system.")
            return
        proxy.set_proxy(enable, proxy_server)


class AutoLoginUtil:
    def __init__(self, shu_config: dict):
        self.user_id = shu_config["user_id"]
        self.user_index = shu_config["user_index"]
        self.password = shu_config["password"]
        self.cookie = shu_config["cookie"]
        self.query_string = shu_config["query_string"]

        self.post_URL = "http://10.10.9.9/eportal/InterFace.do?method=login"
        self.get_URL = f"http://10.10.9.9/eportal/success.jsp?userIndex={self.user_index}&keepaliveInterval=0"

        self.header, self.data = self.construct_header_and_data()

    def construct_header_and_data(self):
        header = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Cookie": self.cookie,
            "Host": "10.10.9.9",
            "Origin": "http://10.10.9.9",
            "Referer": f"http://10.10.9.9/eportal/index.jsp?{self.query_string}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
        }
        data = {
            "userId": self.user_id,
            "password": self.password,
            "queryString": self.query_string,
            "passwordEncrypt": 'true',
            "operatorPwd": '',
            "operatorUserId": '',
            "validcode": '',
            "service": 'shu',
        }
        return header, data

    @staticmethod
    def is_network_accessible():
        try:
            response = requests.get("https://www.baidu.com", timeout=5)
            if response.status_code == 200:
                return True
            return False
        except requests.exceptions.ProxyError:
            try:
                # 如果开了vpn, 填写你的代理地址.
                proxies = {"http": "socks5h://127.0.0.1:7890", "https": "socks5h://127.0.0.1:7890"}
                response = requests.get("https://www.baidu.com", timeout=5, proxies=proxies)
                if response.status_code == 200:
                    return True
                return False
            except requests.exceptions.RequestException as e:
                logger.error(e)
                return False
        except requests.exceptions.RequestException as e:
            logger.error(e)
            return False

    def login(self):
        logger.info("开始自动联网...")
        try:
            response = requests.post(self.post_URL, self.data, headers=self.header)
        except requests.exceptions.RequestException as e:
            logger.error(e)
            return False
        logger.info("post请求状态码{}".format(response.status_code))
        try:
            response = requests.get(self.get_URL).status_code
        except requests.exceptions.RequestException as e:
            logger.error(e)
            return False
        logger.info("get请求状态码{}".format(response))
        if response == 200:
            return True
        return False


if __name__ == '__main__':
    # 填充你自己的参数
    login_config = {
        "user_id": "22721284",
        "user_index": "xxx",
        "password": "xxx",
        "cookie": "xxx",
        "query_string": "xxx",
    }

    alu = AutoLoginUtil(login_config)
    if alu.is_network_accessible() is True:
        logger.info("当前网络已接入！")
        sys.exit(0)

    # 关闭代理. （联网后自己手动开启vpn）
    if ProxyUtil.is_proxy_enabled() is True:
        ProxyUtil.set_proxy(enable=False)

    max_try, time_interval = 10, 5
    for i in range(max_try):
        if alu.login() is True:
            logger.info("登录成功！")
            break
        logger.error("第{}次尝试登录失败，{}s后重试...".format(i + 1, time_interval))
        time.sleep(5)
