import re
import os
import time
import json
import logging
import libtmux
import argparse
import coloredlogs
import configparser
from configobj import ConfigObj


REQUIRED_WINDOWS = {}
RUN_ONCE_WINDOWS = {}
TARGET_NAME = ""
TARGET_IP = ""
TARGET_DIR = ""
TARGET_SESSION = None
TARGET_RECREATED = False

ATTR_PING = True


def setup_options():
    argparser = argparse.ArgumentParser()
    argparser.add_argument('-t', required=True, dest='target', help='Target in [name]:[ip] format.')
    argparser.add_argument('-d', default='default', dest='directory', help='Directory to setup the target in.')
    args = vars(argparser.parse_args())
    logging.debug(args)
    check_options(args)


def check_options(args):
    global TARGET_NAME, TARGET_IP, TARGET_DIR
    target = args['target']
    dir = args['directory']
    # Checking if target is in the format name:ip
    if ":" in target:
        name, ip = target.split(":")
        ip_pattern = r"^[0-9]{1,3}[.][0-9]{1,3}[.][0-9]{1,3}[.][0-9]{1,3}$"
        ip_re = re.compile(ip_pattern)
        ip_found = ip_re.findall(ip)
        if not len(ip_found):
            logging.error("Invalid Target IP provided! Check again.")
            exit(1)
        name_pattern = r"^[a-zA-Z0-9\-_]+$"
        name_re = re.compile(name_pattern)
        name_found = name_re.findall(name)
        if not len(name_found):
            logging.error("Target Name shoud only contain a-z, A-Z, 0-9 and special chars like '_' and '-'.")
            exit(1)
        TARGET_NAME = name
        TARGET_IP = ip
    else:
        logging.error("Invalid target! Target should be in the format [name]:[ip]. Eg., machine1:127.0.0.1")
        exit(1)

    if dir == "default":
        TARGET_DIR = os.getcwd()
    elif not os.path.exists(dir):
        print("'%s' directory does not exist!" % dir)
        choice = input("Should it be created? (y/n) ")
        if choice.lower() in ["yes", "y"]:
            logging.debug("Creating directory '%s'" % dir)
            os.mkdir(dir)
        else:
            logging.error("Create the directory '%s' first!" % dir)
            exit(1)
    else:
        TARGET_DIR = dir
    check_config()


def check_config():
    global ATTR_PING, REQUIRED_WINDOWS, RUN_ONCE_WINDOWS
    try:
        parser = ConfigObj('conf.ini', list_values=True, unrepr=True)
        if 'windows' in parser.sections:
            sec_windows = parser['windows']
            for win in sec_windows.sections:
                commands = sec_windows[win]['commands']
                run_once = sec_windows[win]['run_once']
                REQUIRED_WINDOWS[win] = [commands, run_once]
        if 'general' in parser.sections:
            sec_general = parser['general']
            ATTR_PING = sec_general['ping']
        print(REQUIRED_WINDOWS)
    except Exception as e:
        logging.error(e)
        raise e


def setup_session():
    global TARGET_SESSION, TARGET_RECREATED
    try:
        session_name = TARGET_NAME.lower() + "-" + TARGET_IP.replace(".", "_")
        logging.debug("Checking for %s" % session_name)
        server = libtmux.Server()
        if server.has_session(session_name):
            logging.debug("Session already exists!")
            server.switch_client(session_name)
            TARGET_SESSION = [x for x in server.sessions if x['session_name'] == session_name][0]
        else:
            logging.debug("Creating new session with name '%s'" % session_name)
            TARGET_SESSION = server.new_session(session_name=session_name, start_directory=TARGET_DIR, window_name='test')
            TARGET_SESSION.set_environment('TARGET', TARGET_IP)
            TARGET_SESSION.set_environment('TARGET_NAME', TARGET_NAME)
            TARGET_SESSION.set_environment('TARGET_DIR', TARGET_DIR)
            tmp_win_name = "Home"
            if ATTR_PING:
                tmp_win_name = "Ping"
            TARGET_SESSION.new_window(window_name=tmp_win_name, start_directory=TARGET_DIR)
            TARGET_SESSION.kill_window("test")
            home_win = TARGET_SESSION.windows[0]
            home_win.move_window(0)
            home_pane = home_win.select_pane(0)
            if ATTR_PING:
                home_pane.send_keys('ping -i 5 %s' % TARGET_IP)
        if os.path.exists("{}/.tmux.lock".format(TARGET_DIR)):
            TARGET_RECREATED = True
        else:
            with open("{}/.tmux.lock".format(TARGET_DIR), "w") as file:
                file.write("")
        create_windows(server)
    except Exception as e:
        logging.error(e)
        raise e


def create_windows(server):
    try:
        for window in REQUIRED_WINDOWS:
            if len(TARGET_SESSION.where({"window_name": window})):
                continue
            panes = REQUIRED_WINDOWS[window][0]
            run_once = REQUIRED_WINDOWS[window][1]
            if run_once and TARGET_RECREATED:
                logging.info("Skipping window '%s'" % (window))
                continue
            len_panes = len(panes)
            logging.info("Creating window %s with panes %s" % (window, ", ".join(panes)))
            tmp_window = TARGET_SESSION.new_window(window_name=window, start_directory=TARGET_DIR)
            if len_panes > 1:
                if len_panes > 5:
                    for y in range(4):
                        tmp_window.split_window(start_directory=TARGET_DIR)
                    tmp_window.select_layout("tiled")
                    for y in range(len_panes - 5):
                        tmp_window.split_window(start_directory=TARGET_DIR)
                    tmp_window.select_layout("tiled")
                else:
                    for x in range(len_panes - 1):
                        tmp_window.split_window(start_directory=TARGET_DIR)
                    tmp_window.select_layout("tiled")
            tmp_window.select_pane(0)
            tmp_panes_list = tmp_window.panes
            for x in range(len_panes):
                pane = tmp_panes_list[x]
                cmd = REQUIRED_WINDOWS[window][0][x]
                pane.send_keys(cmd)
    except Exception as e:
        logging.error(e)


def main():
    setup_options()
    setup_session()


if __name__ == '__main__':
    coloredlogs.install(fmt='%(asctime)s %(levelname)s : %(message)s', level='INFO')
    main()
