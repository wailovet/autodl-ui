# 引入time模块，实现延时
import asyncio
import ctypes
import inspect
import json
import os

import logging
from pydoc import cli
from turtle import bgcolor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


try:
    import json5
except ImportError:
    os.system("pip install json5")
    import json5
import time

try:
    import paramiko
except ImportError:
    os.system("pip install paramiko")
    import paramiko

try:
    import sshtunnel
except ImportError:
    os.system("pip install sshtunnel")
    import sshtunnel


global_data = {
    "callback": {},
    "ssh_clients": {},
    "ssh_tunnels": {},
    "ssh_log": {},
    "current_ssh_log": "",
}


def add_api_update_callback(url, callback):
    """添加api更新回调函数"""
    global_data["callback"][url] = callback


def _async_raise(tid, exctype):
    """raises the exception, performs cleanup if needed"""
    tid = ctypes.c_long(tid)
    if not inspect.isclass(exctype):
        exctype = type(exctype)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
    if res == 0:
        raise ValueError("invalid thread id")
    elif res != 1:
        # """if it returns a number greater than one, you're in trouble,
        # and you should call it again with exc=NULL to revert the effect"""
        ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
        raise SystemError("PyThreadState_SetAsyncExc failed")


def stop_thread(thread):
    _async_raise(thread.ident, SystemExit)


selenium_device = {}


def selenium_core():
    try:
        import selenium
    except ImportError:
        os.system("pip install selenium")

    try:
        import seleniumwire
    except ImportError:
        os.system("pip install selenium-wire")

    # 引入selenium库中的webdriver模块，实现对网页的操作
    from selenium import webdriver

    # 引入By Class，辅助元素定位
    from selenium.webdriver.common.by import By

    # 引入ActionChains Class，辅助鼠标移动
    from selenium.webdriver.common.action_chains import ActionChains

    from seleniumwire import webdriver as webdriverwire
    from seleniumwire.request import Request, Response

    def request_interceptor(request: Request):
        """处理请求"""
        logger.debug("request_interceptor", request.method, request.url)

    def response_interceptor(request: Request, response: Response):
        """处理请求响应"""

        # logger.debug("response_interceptor", request.method,
        #       request.url, response.status_code)

        # logger.debug("response content", response.body.decode("utf-8", errors="ignore"))

        base_url = request.url.split("?")[0]
        # logger.debug("base_url", base_url)

        if base_url:
            if "api_data" not in global_data:
                global_data["api_data"] = {}
            if base_url not in global_data["api_data"]:
                global_data["api_data"][base_url] = {}
            global_data["api_data"][base_url].update(
                {
                    "response": json.loads(
                        response.body.decode("utf-8", errors="ignore"),
                        strict=False,
                    ),
                }
            )

            if (
                base_url in global_data["callback"]
                and global_data["callback"][base_url]
            ):
                callback = global_data["callback"][base_url]
                print(
                    "callback api_data",
                    json.dumps(global_data["api_data"][base_url]["response"], indent=4),
                )
                callback(global_data["api_data"][base_url]["response"])

            # logger.debug("global_data", json.dumps(global_data, indent=4))

    options = webdriver.ChromeOptions()
    options.add_argument("--ignore-certificate-errors")
    # 设置用户数据目录的路径
    user_data_dir = os.path.join(os.path.dirname(__file__), "user_data")
    # 设置Chrome的用户数据目录
    options.add_argument(f"--user-data-dir={user_data_dir}")

    # url正则表达式集合
    scopes = set()
    scopes.add("https?://.+/api/v1/instance")
    ignore_http_methods = [
        "OPTIONS",
        "HEAD",
        "CONNECT",
        "TRACE",
        "PATCH",
    ]
    seleniumwire_options = {
        # 过滤域名
        "exclude_hosts": ["www.exclude.com"],
        # 过滤请求方法
        "ignore_http_methods": ignore_http_methods,
        "verify_ssl": False,  # 不验证证书
        "enable_logging": True,
        "request_storage": "memory",  # 缓存到内存
        # "request_storage_base_dir": request_storage_base_dir,  # 设置请求缓存的目录
        "request_storage_max_size": 100,  # Store no more than 100 requests in memory
    }

    try:
        driver = webdriverwire.Chrome(
            options=options,
            seleniumwire_options=seleniumwire_options,
        )
    except Exception as e:
        logger.error("selenium_core", e)
        return
    selenium_device["driver"] = driver
    logger.debug("selenium_device", selenium_device)

    # driver.request_interceptor = request_interceptor
    driver.response_interceptor = response_interceptor
    driver.scopes = list(scopes)

    # 打开谷歌浏览器
    # driver = webdriver.Chrome()

    driver.minimize_window()
    # 打开网页
    # 将URL替换为需要操作的网址
    driver.get("https://www.autodl.com/console/instance/list")

    # 等待页面加载
    while True:
        time.sleep(1)
        if "/login" in driver.current_url:
            driver.maximize_window()
            break

    # 如果网址带着 "/login?" 说明没有登录
    if "/login" in driver.current_url:
        driver.maximize_window()
        logger.debug("登录中....")
        while "/login" in driver.current_url:
            # 等待页面加载
            time.sleep(1)
        driver.minimize_window()

    # https://www.autodl.com/console/instance/list
    # 将URL替换为需要操作的网址
    driver.get("https://www.autodl.com/console/instance/list")


def post_api(url, data):
    """同步发送post请求"""
    logger.debug("post_api", url, data)
    script = f"""
        let xhr = new XMLHttpRequest(); 
        xhr.open('POST', '{url}', false);
        console.log('xhr.open', xhr.open);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.onreadystatechange = function() {{
            console.log('xhr.readyState', xhr.readyState);
            if (xhr.readyState === 4 && xhr.status === 200) {{
                console.log('请求成功');
            }}
        }}
        xhr.send(JSON.stringify({json.dumps(data)})); 
        """
    logger.debug("script", script)
    selenium_device["driver"].execute_script(script)


def get_innerText_from_selecter(p):
    return selenium_device["driver"].execute_script(
        f"return document.querySelector('{p}').innerText"
    )


def click_from_selecter(p):
    s = f"document.querySelector('{p}').click()"
    print("click_from_selecter", s)
    return selenium_device["driver"].execute_script(
        f"document.querySelector('{p}').click()"
    )


def mouseenter_from_selecter(p):
    return selenium_device["driver"].execute_script(
        f"document.querySelector('{p}').dispatchEvent(new Event('mouseenter'))"
    )


def input_from_selecter(p, value):
    script = f"""
            var callback = arguments[arguments.length - 1];
            await (async function(){{
                async function sleep(ms) {{
                    return new Promise(resolve => setTimeout(resolve, ms));
                }}
                let dom = document.querySelector("{p}");
                dom.focus(); 
                await sleep(100);  
                dom.value = '{value}';
                await sleep(100); 
                dom.dispatchEvent(new Event('input')); 
                await sleep(100); 
                dom.dispatchEvent(new Event('change')); 
                await sleep(100);  
                callback(0)
            }})();
            
    """
    selenium_device["driver"].execute_async_script(script)


def exec_js(js):
    return selenium_device["driver"].execute_script(js)


def find_uuid(uuid):
    try:
        # logger.debug("find_uuid", uuid)
        for i in range(1, 10):
            # logger.debug("i:", i)
            suuid = get_innerText_from_selecter(
                f"#app div.el-table__body-wrapper.is-scrolling-none > table > tbody > tr:nth-child({i}) > td.el-table_1_column_1.el-table__cell > div > div > div:nth-child(3)"
            )
            logger.debug("uuid:", suuid)
            if suuid == uuid:
                logger.debug("找到uuid对应的元素 :", i)
                return i

    except Exception as e:
        logger.debug("select_uuid error", e)
    return -1


locker = {}


# 设置延后10分钟关机
def set_shutdown_at_delay(row_id):
    try:
        if "set_shutdown_at_delay" in locker and locker["set_shutdown_at_delay"] == 1:
            logger.debug("set_shutdown_at_delay is running")
            return 1
        locker["set_shutdown_at_delay"] = 1
        import datetime

        now = datetime.datetime.now()
        now = now + datetime.timedelta(minutes=10)
        next_time = now.strftime("%Y-%m-%d %H:%M")

        # 弹出设置框
        try:
            click_from_selecter(
                f"#app > div.user-console > div.data-list-common > div.page-content > div.table-list > div > div.loading-box.instance-table > div.table-box.fixed-height > div > div.el-table__body-wrapper.is-scrolling-none > table > tbody > tr:nth-child({row_id}) > td.el-table_1_column_7.el-table__cell > div > div > div > button"
            )
        except Exception as e:
            # 如果已经设置尝试使用下面的
            click_from_selecter(
                f"#app > div.user-console > div.data-list-common > div.page-content > div.table-list > div > div.loading-box.instance-table > div.table-box.fixed-height > div > div.el-table__body-wrapper.is-scrolling-none > table > tbody > tr:nth-child({row_id}) > td.el-table_1_column_7.el-table__cell > div > div > div > span.timed-shutdown > div > button:nth-child(1)"
            )
        time.sleep(1)
        input_from_selecter(
            "#app > div.user-console > div.data-list-common > div.page-content > div.table-list > div > div:nth-child(2) > div > div > div.el-dialog__body > form > div:nth-child(1) > div > div > input",
            next_time,
        )

        # 点击确定
        click_from_selecter(
            "#app > div.user-console > div.data-list-common > div.page-content > div.table-list > div > div:nth-child(2) > div > div > div.el-dialog__footer > button.el-button.el-button--primary.el-button--small"
        )
    except Exception as e:
        logger.debug("set_shutdown_at_delay error", e)
        return 1

    locker.pop("set_shutdown_at_delay", None)
    return 0


_ui_log = None


def log_main_ui(msg, *args, **kwargs):
    if _ui_log:
        _ui_log(msg, *args, **kwargs)


_log_ssh_cmd = None


def log_ssh_cmd(msg, *args, **kwargs):
    if _log_ssh_cmd:
        _log_ssh_cmd(msg, *args, **kwargs)

_global_task_queue = {}


def add_global_task(name, task, interval_seconds=1):
    _global_task_queue[name] = {
        "task_func": task,
        "interval_seconds": interval_seconds,
    }


def delete_global_task(name):
    print("del_global_task", name)
    _global_task_queue.pop(name, None)


# 启动服务
def start_service(module, no_gpu=False):
    try:
        import datetime

        now = datetime.datetime.now()
        now = now + datetime.timedelta(minutes=5)
        now = now.strftime("%Y-%m-%d %H:%M")
        # {"instance_uuid":"0b0b4098ff-995d66bb","shutdown_at":"2025-04-17 14:52"}
        cloud_info = module.get("cloud_info", {})
        instance_uuid = cloud_info.get("uuid", "")
        log_main_ui("开始启动服务...")
        row_id = find_uuid(instance_uuid)
        if row_id == -1:
            log_main_ui("找不到对应镜像的uuid")
            raise Exception("instance_uuid not found")
        # 设置延后10分钟关机
        set_shutdown_at_delay(row_id)
        log_main_ui("设置关机时间")
        # 查询是否是开机状态
        if cloud_info.get("status") == "shutdown":
            log_main_ui("开机中...")

            if not no_gpu:
                # 启动
                selecter_p = "#app > div.user-console > div.data-list-common > div.page-content > div.table-list > div > div.loading-box.instance-table > div.table-box.fixed-height > div > div.el-table__body-wrapper.is-scrolling-none > table > tbody > tr.el-table__row.el-table__row--striped > td.el-table_1_column_10.el-table__cell > div > div > button"
                selecter_p = selecter_p.replace(
                    "> tr.el-table__row.el-table__row--striped",
                    f"> tr:nth-child({row_id})",
                )
                click_from_selecter(selecter_p)

            else:
                #  document.querySelectorAll(".el-dropdown-menu")[1].querySelector("div:nth-child(1) > li").click()

                # selecter_p = ".el-dropdown-menu > div:nth-child(1) > li"
                # click_from_selecter(selecter_p)
                exec_js(
                    f"""
                    document.querySelectorAll(".el-dropdown-menu")[{row_id-1}].querySelector("div:nth-child(1) > li").click()
                    """
                )
                time.sleep(1)

            for _ in range(1, 5):
                # 等待启动
                time.sleep(1)
                try:
                    get_innerText_from_selecter(
                        "body > div.el-overlay.is-message-box > div > div.el-message-box__btns > button.el-button.el-button--default.el-button--small.el-button--primary"
                    )
                    break
                except Exception as e:
                    pass

            click_from_selecter(
                "body > div.el-overlay.is-message-box > div > div.el-message-box__btns > button.el-button.el-button--default.el-button--small.el-button--primary"
            )

        ssh_port = cloud_info.get("ssh_port", -1)
        root_password = cloud_info.get("root_password", "")
        # ssh -p 47301 root@connect.cqa1.seetacloud.common
        ssh_command = cloud_info.get("ssh_command", "")
        _t = ssh_command.split(" ")[3]
        ssh_user = _t.split("@")[0]
        ssh_host = _t.split("@")[1]
        start_command = module.get("start_command", "")

        # 登录ssh
        if instance_uuid in global_data["ssh_clients"]:
            # 断开ssh
            global_data["ssh_clients"][instance_uuid].close()
            global_data["ssh_clients"].pop(instance_uuid)
            log_main_ui("SSH: 存在连接，断开连接")
        global_data["ssh_clients"][instance_uuid] = paramiko.SSHClient()
        global_data["ssh_clients"][instance_uuid].set_missing_host_key_policy(
            paramiko.AutoAddPolicy()
        )
        for i in range(1, 10):
            try:
                log_main_ui("SSH: 连接中...")
                global_data["ssh_clients"][instance_uuid].connect(
                    ssh_host,
                    port=ssh_port,
                    username=ssh_user,
                    password=root_password,
                )
                log_main_ui("SSH: 连接成功")
                break
            except Exception as e:
                log_main_ui("SSH: 连接失败，重试中...")
                logger.debug("ssh connect error:", e)
                time.sleep(10)
        # 判断是否已经连接成功
        if global_data["ssh_clients"][instance_uuid].get_transport() is None:
            log_main_ui("SSH: 连接失败")
            raise Exception("ssh connect error")
        if (
            global_data["ssh_clients"][instance_uuid].get_transport().is_active()
            == False
        ):
            log_main_ui("SSH: 连接已断开")
            raise Exception("ssh connect active error")
        log_main_ui("SSH: 连接成功, 启动服务")

        def async_run_remote_command():
            # 启动服务
            stdin, stdout, stderr = global_data["ssh_clients"][
                instance_uuid
            ].exec_command(
                start_command,
                get_pty=True,
                bufsize=1,
            )

            log_main_ui("服务启动中...")

            while not stdout.channel.exit_status_ready():
                if stdout.channel.recv_ready():
                    line = stdout.readline()
                    if instance_uuid not in global_data["ssh_log"]:
                        global_data["ssh_log"][instance_uuid] = ""
                    global_data["ssh_log"][instance_uuid] += line
                    if global_data["current_ssh_log"] == instance_uuid:
                        log_ssh_cmd(global_data["ssh_log"][instance_uuid])

                if stderr.channel.recv_ready():
                    line = stderr.readline()
                    if instance_uuid not in global_data["ssh_log"]:
                        global_data["ssh_log"][instance_uuid] = ""
                    global_data["ssh_log"][instance_uuid] += line
                    if global_data["current_ssh_log"] == instance_uuid:
                        log_ssh_cmd(global_data["ssh_log"][instance_uuid])
            log_main_ui("服务结束")

        threading.Thread(target=async_run_remote_command).start()

    except Exception as e:
        logger.debug("enter_module error", e)
        log_main_ui("服务启动失败:" + str(e))
        pass

    try:
        must_tunnel_port = module.get("must_tunnel_port", -1)
        if must_tunnel_port != -1:
            # 转发端口
            log_main_ui("SSH: 转发端口...")

            if instance_uuid in global_data["ssh_tunnels"]:
                # 断开ssh
                global_data["ssh_tunnels"][instance_uuid].stop()
                global_data["ssh_tunnels"].pop(instance_uuid)

            global_data["ssh_tunnels"][instance_uuid] = sshtunnel.SSHTunnelForwarder(
                f"{ssh_host}",
                ssh_port=ssh_port,
                ssh_username=ssh_user,
                ssh_password=root_password,
                remote_bind_address=(
                    "127.0.0.1",
                    must_tunnel_port,
                ),
                local_bind_address=(
                    "127.0.0.1",
                    must_tunnel_port,
                ),
            )

            # 转发端口
            log_main_ui("SSH: 端口转发中...")

            # reverse_forward_tunnel(80, "localhost", 8080, transport)
            global_data["ssh_tunnels"][instance_uuid].start()
            log_main_ui("SSH: 端口转发成功")

    except Exception as e:
        logger.debug("ssh_tunnel error", e)
        log_main_ui("SSH: 端口转发失败:" + str(e))
        pass

    def ___task():
        log_main_ui("开始续期服务关闭时间...")
        row_id = find_uuid(instance_uuid)
        set_shutdown_at_delay(row_id)

    add_global_task(
        f"set_shutdown_at_delay_{instance_uuid}",
        ___task,
        interval_seconds=60 * 8,
    )


def ui_core():
    # pip install flet
    try:
        import flet
    except ImportError:
        os.system("pip install flet")
        import flet
    import flet as ft

    def main(page: flet.Page):

        page.title = "autodl-console"
        # page.vertical_alignment = "center"

        main_row = ft.ResponsiveRow(
            controls=[],
        )

        # 进入时候加载动画
        rive = ft.ProgressBar()
        container = ft.Container(
            content=rive,
            width="100vw",
        )

        buttons_view = ft.Column(
            [
                ft.Button(
                    text="刷新列表",
                    on_click=lambda e: click_from_selecter(
                        "#app > div.user-console > div.data-list-common > div.page-content > div.content-header > div:nth-child(1) > button.el-button.el-button--default.el-button--small.refresh-btn"
                    ),
                ),
                ft.Button(
                    text="刷新页面",
                    on_click=lambda e: exec_js(
                        "location.href='https://www.autodl.com/console/instance/list';location.reload();"
                    ),
                ),
            ],
            col=1,
        )

        cards_view = ft.Column(
            scroll="auto",
            col=8,
        )

        # 日志框
        log_view = ft.Text(
            value="",
            size=10,
            selectable=True,
        )

        ssh_log_view = ft.Text(
            value="",
            size=10,
            selectable=True,
            # 自动换行
        )

        c1 = ft.Column(
            [
                ft.Container(
                    content=ft.Row([log_view]),
                    padding=10,
                ),
            ],
            scroll="auto",
            height=300,
        )
        c2 = ft.Column(
            [
                ft.Container(
                    content=ft.Row([ssh_log_view]),
                    padding=10,
                ),
            ],
            scroll="auto",
            height=300,
            width=500,
        )
        c2_dialog = None
        c2_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("SSH日志"),
            content=c2,
            actions=[
                ft.TextButton("关闭", on_click=lambda e: page.close(c2_dialog)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        log_container = ft.Column(
            [
                ft.Card(
                    content=c1,
                ),
                # ft.Card(
                #     content=c2,
                # ),
            ],
            col=2,
        )

        main_row.controls = [buttons_view, cards_view, log_container]

        def _ui_log_inner(msg, *args, **kwargs):
            if kwargs.get("new_line", True):
                msg = "\n" + msg
            log_view.value = log_view.value + msg

            page.update()
            c1.scroll_to(offset=-1)

        global _ui_log
        _ui_log = _ui_log_inner

        def _log_ssh_cmd_inner(msg, *args, **kwargs):
            ssh_log_view.value = msg
            page.update()
            c2.scroll_to(offset=-1)

        global _log_ssh_cmd
        _log_ssh_cmd = _log_ssh_cmd_inner

        def update_text_view(data):
            try:
                if "update_text_view" in locker and locker["update_text_view"] == 1:
                    logger.debug("update_text_view is running")
                    return 1
                locker["update_text_view"] = 1
                # 刷新页面
                # logger.debug("update_text_view", data)

                # 清空cards_view
                cards_view.controls.clear()

                # config.json5
                config_data = {}
                with open("config.json5", "r", encoding="utf-8") as f:
                    config_data = json5.loads(f.read())

                modules = config_data.get("modules", [])

                def gen_start_module(module, no_gpu=False):
                    def __t(ce: ft.ControlEvent):
                        start_service(module, no_gpu)

                    return __t

                def open_webui(module):
                    def __t(ce: ft.ControlEvent):
                        remote_webui_addr = module.get("remote_webui_addr", "")
                        if remote_webui_addr == "":
                            return
                        os.system(f"start {remote_webui_addr}")

                    return __t

                def open_ssh_log(module):
                    def __t(ce: ft.ControlEvent):
                        uuid = module.get("cloud_info", {}).get("uuid", "")
                        global_data["current_ssh_log"] = uuid
                        page.open(c2_dialog)

                    return __t

                def close_instance(module):
                    def __t(ce: ft.ControlEvent):
                        try:
                            uuid = module.get("cloud_info", {}).get("uuid", "")
                            row_id = find_uuid(uuid)
                            # 关闭实例
                            selector_p = f"#app > div.user-console > div.data-list-common > div.page-content > div.table-list > div > div.loading-box.instance-table > div.table-box.fixed-height > div > div.el-table__body-wrapper.is-scrolling-none > table > tbody > tr.el-table__row.el-table__row--striped > td.el-table_1_column_10.el-table__cell > div > div > button"
                            selector_p = selector_p.replace(
                                "> tr.el-table__row.el-table__row--striped",
                                f"> tr:nth-child({row_id})",
                            )

                            text = get_innerText_from_selecter(selector_p).strip()
                            if text.index("关机") != -1:
                                # 关闭ssh
                                delete_global_task(f"set_shutdown_at_delay_{uuid}")
                                click_from_selecter(selector_p)
                                time.sleep(2)
                                click_from_selecter(
                                    "body > div.el-overlay.is-message-box > div > div.el-message-box__btns > button.el-button.el-button--default.el-button--small.el-button--primary",
                                )
                            else:
                                print("text:", text, text.index("关机"))
                                print("selector_p:", selector_p)

                        except Exception as e:
                            logger.debug("close_instance error", e)
                            pass
                    return __t

                for module in modules:
                    mirror_name = module.get("mirror_name", "")
                    cloud_info = {}
                    for data_item in data.get("data", {"list": []}).get("list", []):
                        print(
                            "reproduction_uuid !=",
                            mirror_name,
                            "||",
                            data_item.get("reproduction_uuid"),
                        )
                        if data_item.get("reproduction_uuid") == mirror_name:
                            cloud_info = data_item
                            break
                    module["cloud_info"] = cloud_info
                    if cloud_info == {}:
                        show_info = "未找到已经部署的镜像"
                    else:
                        # machine_alias/uuid/region_name/snapshot_gpu_alias_name/status/gpu_idle_num/timed_shutdown_at.Time
                        show_info = (
                            f"镜像名称: {mirror_name}\n"
                            + f"云端别名: {cloud_info.get('machine_alias', '')}\n"
                            + f"云端ID: {cloud_info.get('uuid', '')}\n"
                            + f"地区: {cloud_info.get('region_name', '')}\n"
                            + f"GPU: {cloud_info.get('snapshot_gpu_alias_name', '')}\n"
                            + f"状态: {cloud_info.get('status', '')}\n"
                            + f"GPU空闲数: {cloud_info.get('gpu_idle_num', '')}\n"
                            + f"关机时间: {cloud_info.get('timed_shutdown_at', {}).get('Time', '')}\n"
                        )
                    card = ft.Card(
                        content=ft.Container(
                            content=ft.Column(
                                [
                                    ft.ListTile(
                                        leading=ft.Icon(ft.Icons.ALBUM),
                                        title=ft.Text(module.get("name", "")),
                                        subtitle=ft.Text(show_info),
                                    ),
                                    ft.Row(
                                        [
                                            ft.TextButton(
                                                text="启动",
                                                expand=True,
                                                on_click=gen_start_module(module),
                                                disabled=cloud_info == {},
                                            ),
                                            ft.TextButton(
                                                text="无卡模式启动",
                                                expand=True,
                                                on_click=gen_start_module(
                                                    module, no_gpu=True
                                                ),
                                                disabled=cloud_info == {},
                                            ),
                                            ft.TextButton(
                                                text="关机",
                                                expand=True,
                                                on_click=close_instance(module),
                                                disabled=cloud_info == {},
                                            ),
                                            ft.TextButton(
                                                text="查看日志",
                                                expand=True,
                                                on_click=open_ssh_log(module),
                                                disabled=cloud_info == {},
                                            ),
                                            ft.TextButton(
                                                text="打开webui",
                                                expand=True,
                                                on_click=open_webui(module),
                                                disabled=cloud_info == {},
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            padding=10,
                        )
                    )
                    cards_view.controls.append(card)
                    page.controls = [main_row]
                    page.update()

            except Exception as e:
                logger.debug("update_text_view error", e)
            locker.pop("update_text_view", None)

        add_api_update_callback(
            "https://www.autodl.com/api/v1/instance",
            update_text_view,
        )

        # 从左上角开始
        page.add(container)

    flet.app(target=main)



# 不严格的定时器,一秒执行一次
def _timer_for_task():
    while True:
        time.sleep(1)
        for name, task in _global_task_queue.items():
            try:
                task_func = task.get("task_func", None)
                if task_func is None:
                    continue
                last_run_time = task.get("last_run_time", 0)
                interval_seconds = task.get("interval_seconds", 1)
                if time.time() - last_run_time > interval_seconds:
                    task_func()
                    task["last_run_time"] = time.time()

            except Exception as e:
                logger.error("task error", e)
                pass


if __name__ == "__main__":
    import threading

    # 启动selenium线程
    # selenium_core()
    t = threading.Thread(target=selenium_core)
    t.start()

    # 启动定时器线程
    t = threading.Thread(target=_timer_for_task)
    t.start()

    ui_core()
    # 结束线程
    stop_thread(t)
