import requests
import argparse
import re
import time
from bs4 import BeautifulSoup
import json
import psutil
import getpass
import socket
import os
import sys
from urllib.parse import urlsplit
from pathlib import Path
from des import str_enc

# 正则表达式匹配IPv4地址


def is_ipv4(ip):
    pattern = r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
    if re.match(pattern, ip):
        return True
    else:
        print("IP address format error!")
        return False


# 获取本地校园IP地址，校园IP地址一般以"172"开头


def get_local_ip():
    try:
        # 获取所有网络接口信息
        interfaces = psutil.net_if_addrs()
        ip_list = []
        for interface_name, interface_addresses in interfaces.items():
            for address in interface_addresses:
                # 检查是否是IPv4地址且是校园网IP
                if address.family == socket.AF_INET and address.address.startswith(
                    ("172.", "192.168.")
                ):
                    ip_list.append(address.address)
                    print(
                        f"Network interface detected, Interface: {interface_name}, Address: {address}"
                    )
        if len(ip_list) == 0:
            raise Exception(
                "Campus network IP not detected. Please ensure you are correctly connected to the campus network via WIFI or Ethernet!"
            )
        else:
            return ip_list
    except:
        raise Exception("Failed to get local IP address!")


# 通过des.py的加密函数加密


def strEnc(data, firstKey, secondKey, thirdKey):
    return str_enc(data, firstKey, secondKey, thirdKey)


# # 调用Node.js执行des.js里的加密函数
# def strEnc(data, firstKey, secondKey, thirdKey):
#     result = subprocess.run(
#         ['node', 'des.js', data, firstKey, secondKey, thirdKey],
#         capture_output=True, text=True
#     )

#     # 检查命令执行结果
#     if result.returncode == 0:
#         print("Encryption result: ", result.stdout.strip())
#     else:
#         raise Exception("An error occurred during execution: ", result.stderr)

#     return result.stdout.strip()

# 用于格式化输出online_list


def format_online_list_print(data_list):
    print("online_list:")
    # 获取字段名列表，假设所有字典有相同的字段
    headers = list(data_list[0].keys())

    # 打印表头，每个字段宽度设置为10
    header_row = "|".join(f"{header:<10}" for header in headers)
    print("-" * len(header_row))  # 打印分隔线
    print(header_row)
    print("-" * len(header_row))  # 打印分隔线

    # 打印每行数据
    for item in data_list:
        formatted_line = "|".join(f"{str(item[key]):<10}" for key in headers)
        print(formatted_line)
    print("-" * len(header_row))  # 打印分隔线


def extract_value_by_id_or_name(soup, attribute_type, attribute_value):
    """
    Extracts the value of an HTML element identified by its ID or name attribute.

    Parameters:
    - soup: BeautifulSoup object representing the HTML document.
    - attribute_type: A string specifying the type of attribute to search for ('id' or 'name').
    - attribute_value: The value of the 'id' or 'name' attribute to search for.

    Returns:
    - The value of the 'value' attribute of the found element, or None if the element is not found.
    """
    if attribute_type not in ["id", "name"]:
        raise ValueError(
            f"Attribute type must be 'id' or 'name', but got: {attribute_type}!"
        )

    if attribute_type == "id":
        element = soup.find(id=attribute_value)
    else:  # attribute_type == 'name'
        element = soup.find(attrs={"name": attribute_value})

    if element:
        return element.get("value")
    else:
        raise Exception(f"Element with {attribute_type} = {attribute_value} not found!")


# 实际登录函数


def do_login(username, password, ip, cookies=None):
    if not is_ipv4(ip):
        return False
    # 初始URL，可能是你想访问的网站的URL，这个网站将你重定向到SSO登录页面
    initial_url = f"http://172.20.30.2:8080/Self/sso_login?login_method=1&wlan_user_ip={ip}&wlan_user_ipv6=&wlan_user_mac=000000000000&wlan_ac_ip=172.20.30.254&wlan_ac_name=&mac_type=1&authex_enable=&type=1"

    print(f"Initial login URL: {initial_url}")

    # 创建一个session对象，这样Cookies和会话信息就可以在请求之间保持了
    session = requests.Session()
    for name, value in (cookies or {}).items():
        session.cookies.set(
            name, value, domain="sso.dlut.edu.cn", path="/", secure=True
        )

    # 首先访问初始URL
    response = session.get(initial_url)

    # 使用BeautifulSoup解析HTML
    soup = BeautifulSoup(response.text, "lxml")

    # 查找id为"lt"的元素
    lt_value = extract_value_by_id_or_name(soup, "id", "lt")
    print("lt:", lt_value)

    # 查找name为"execution"的元素
    execution_value = extract_value_by_id_or_name(soup, "name", "execution")
    print("execution:", execution_value)

    # 查找name为"_eventId"的元素
    event_id_value = extract_value_by_id_or_name(soup, "name", "_eventId")
    print("_eventId:", event_id_value)

    # 检查是否被重定向到SSO登录页
    if response.history:
        # SSO登录表单的URL，这通常是在你被重定向到SSO登录页面时的URL
        # sso_login_url = "https://sso.dlut.edu.cn/cas/login?service=https%3A%2F%2Fportal.dlut.edu.cn%2Ftp%2F"
        sso_login_url = response.url
        print(f"跳转到sso登录页面: {sso_login_url}")

        # 准备登录数据，这个需要根据SSO页面的具体要求来填写
        # 在实际情况中，可能需要额外的字段，比如CSRF令牌等
        login_data = {
            "rsa": strEnc(username + password + lt_value, "1", "2", "3"),
            "ul": len(username),
            "pl": len(password),
            "sl": 0,
            "lt": lt_value,
            "execution": execution_value,
            "_eventId": event_id_value,
        }

        # 提交登录表单
        login_response = session.post(sso_login_url, data=login_data)

        # 只有最终进入校园网自助服务首页才算认证成功。
        destination = urlsplit(login_response.url)
        if destination.hostname == "172.20.30.2" and destination.path.rstrip("/") == "/Self/dashboard":
            print("Redirection...")

            time.sleep(2)  # 等待2秒，防止后台新登录的数据还未刷新
            # 访问设备在线列表，并打印
            online_list_url = f"http://172.20.30.2:8080/Self/dashboard/getOnlineList"
            online_list_response = session.get(online_list_url)
            online_list = json.loads(online_list_response.text)
            format_online_list_print(online_list)
        else:
            login_soup = BeautifulSoup(login_response.content, "lxml")
            if login_soup.find("input", attrs={"name": "PM1"}):
                print("Login requires SMS verification. Complete verification in Edge and refresh the cookie file.")
            else:
                print("Login failed: the server did not reach the campus dashboard. Check credentials and cookie validity.")
            return False
    else:
        raise Exception("No redirection, direct access!")
    return True


# 处理每次登录


def login(username, password, ip, cookies=None):

    if not username:
        username = input("Please enter your username: ")

    if not password:
        password = getpass.getpass("Please enter your password: ")

    # 打印参数
    print(
        f"Current login information: Username: {username}, Password: ******, IP: {ip}"
    )

    max_attempts = 3
    attempt_count = 1

    while attempt_count < max_attempts:
        try:
            # 尝试登录
            print(f"Attempting to log in for the {attempt_count}th time...")
            if do_login(username, password, ip, cookies):
                break
            else:
                return (-1, f"ip: {ip}, Login failed!")

        except Exception as e:
            # 如果操作失败，打印错误消息（或进行其他错误处理）
            print(f"Login failed: {e}, retrying...")
            attempt_count += 1
            time.sleep(3)  # 等待3秒

    if attempt_count == max_attempts:
        return (-1,f"ip: {ip}, Reached the maximum number of login attempts, login failed!")
    else:
        return (
            0, f"ip: {ip}, Please confirm if have successfully connected to the network."
        )


def load_config(path):
    """Read local credentials without including their contents in error messages."""
    with Path(path).open(encoding="utf-8-sig") as config_file:
        config = json.load(config_file)
    if not isinstance(config, dict) or any(
        key not in {"username", "password", "cookies_file"}
        or not isinstance(value, str)
        for key, value in config.items()
    ):
        raise ValueError("Invalid configuration")
    return config


def main():
    # 创建 ArgumentParser 对象
    parser = argparse.ArgumentParser(description="Processing required parameters")

    # 添加参数
    parser.add_argument("-u", "--username", type=str, help="The username")
    parser.add_argument("-p", "--password", type=str, help="The password")
    parser.add_argument("-i", "--ip", type=str, help="The IP address")
    parser.add_argument("-r", "--refresh", action="store_true", help="Whether or not refresh all the adapters before log in")

    parser.add_argument("--cookies", type=str, help="Path to an Edge SSO cookie JSON file")
    parser.add_argument("--config", type=Path, help="Path to local login configuration JSON")

    # 解析命令行参数
    args = parser.parse_args()
    config_path = args.config or Path(__file__).with_name("config.local.json")
    config = {}
    if args.config is not None or config_path.exists():
        try:
            config = load_config(config_path)
        except (OSError, ValueError):
            parser.error("Cannot read login configuration; check its path, JSON format and string fields.")
    if args.username is None:
        args.username = config.get("username")
    if args.password is None:
        args.password = config.get("password")
    if args.cookies is None and config.get("cookies_file"):
        args.cookies = config_path.parent / config["cookies_file"]
    cookies = None
    if args.cookies:
        try:
            with open(args.cookies, encoding="utf-8-sig") as cookie_file:
                cookies = json.load(cookie_file)
        except (OSError, ValueError):
            parser.error("Cannot read cookie JSON file; check its path and JSON format.")
        if not isinstance(cookies, dict) or not cookies or not all(
            isinstance(name, str) and name and isinstance(value, str) and value
            for name, value in cookies.items()
        ):
            parser.error("Cookie JSON must be a non-empty object of cookie names and string values.")

    if args.refresh:
        print("Refreshing adapters...")
        os.popen("ipconfig /release")
        os.popen("ipconfig /renew")
        time.sleep(3)

    ret_value = -1

    if args.ip:
        ret, msg = login(args.username, args.password, args.ip, cookies)
        ret_value = ret
        print(msg)
    else:
        ip_list = get_local_ip()
        result = []
        for ip in ip_list:
            result.append(login(args.username, args.password, ip, cookies))
        for ret, r in result:
            print(r)
            if ret == 0:
                ret_value = 0

    return ret_value

if __name__ == "__main__":
    sys.exit(main())
