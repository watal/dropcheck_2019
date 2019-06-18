# -*- coding:utf-8 -*-

import subprocess
import multiprocessing as mp
import time
import os

import json
import yaml


CONFIG_PATH = 'config.yaml'
REPORT_PATH = 'dat/dropcheck_report.json'


def open_config():
    '''Get DNS address from config'''

    # ファイルからDNSアドレスを取得（キャッシュサーバを指定して取りに行こう）
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r') as f:
            try:
                config = yaml.load(f)
            except ValueError:
                config = {'address': {'dns_v4_prime': '1.1.1.1', 'dns_v4_second': '1.0.0.1',
                                      'dns_v6_prime': '2606:4700:4700::1111', 'dns_v6_second': '2606:4700:4700::1001'}}
    else:
        config = {'address': {'dns_v4_prime': '1.1.1.1', 'dns_v4_second': '1.0.0.1',
                              'dns_v6_prime': '2606:4700:4700::1111', 'dns_v6_second': '2606:4700:4700::1001'}}

    return config


def get_ip_info(command, result_key, q):
    '''Get IP information with ifconfig'''

    # スペース区切りでifconfigの結果を取得
    ifconfig_rslt = subprocess.check_output(
        command, shell=True).decode('utf-8')

    #  行ごとに分割
    ip_info_line = ifconfig_rslt.rstrip('\n').split('\n')

    # パースして辞書に格納
    ip_info = {'inet': '', 'inet6': {}}
    for i in ip_info_line:
        line = i.split()
        if(line[0] == 'inet'):
            ip_info[line[0]] = {line[2]: line[3], line[4]: line[5]}
        elif(line[0] == 'inet6'):
            ip_info[line[0]][line[1]] = {line[2]: line[3], line[4]: line[5]}

    print('FINISH: {}'.format(result_key))
    q.put([result_key, ip_info])


def get_ping(command, result_key, q):
    '''ping and ping6'''

    ping_rslt = subprocess.check_output(command, shell=True).decode('utf-8')

    # 結果をパース
    ping_rslt_line = ping_rslt.rstrip('\n').split('\n')
    ping_out = {}
    ping_out['dst'] = ping_rslt_line[0].split()[1]
    ping_out['send'] = ping_rslt_line[1].split()[0]
    ping_out['recv'] = ping_rslt_line[1].split()[3]
    ping_out['loss'] = ping_rslt_line[1].split()[6]
    ping_out['round-trip'] = {}

    # round_tripの記録
    round_trip_item = ping_rslt_line[2].split()[1].split('/')
    round_trip_value = ping_rslt_line[2].split()[3].split('/')
    for i in range(len(round_trip_item)):
        ping_out['round-trip'][round_trip_item[i]] = round_trip_value[i]

    print('FINISH: {}'.format(result_key))
    q.put([result_key, ping_out])


def get_dns(command, result_key, q):
    '''name resolve with dig'''

    dig_rslt = subprocess.check_output(command, shell=True).decode('utf-8')
    dns = {'server': command.split()[3].lstrip(
        '@'), 'result': dig_rslt.rstrip('\n')}

    print('FINISH: {}'.format(result_key))
    q.put([result_key, dns])


def get_http(command, result_key, q):
    '''get http status code'''

    http_rslt = subprocess.check_output(
        command, shell=True).decode('utf-8').rstrip('\n')

    print('FINISH: {}'.format(result_key))
    q.put([result_key, http_rslt])


def get_trace(command, result_key, q):
    '''traceroute'''

    trace_rslt = subprocess.check_output(command, shell=True).decode('utf-8')
    trace = json.loads(trace_rslt)

    print('FINISH: {}'.format(result_key))
    q.put([result_key, trace])


def dropcheck(tasks):
    '''run Dropcheck and make report'''

    dropcheck_report = {}

    # 並列処理用のキュー
    q = mp.Queue()

    jobs, args = [], []
    for i in tasks:
        jobs += [eval('get_' + tasks[i]['kind'])]
        args += [(tasks[i]['command'], i, q)]

    for job, arg in zip(jobs, args):
        mp.Process(target=job, args=arg).start()

    for i in args:
        report = q.get()
        # 一度関数に渡しといたkeyで辞書に格納。絶対もっといいやり方ある....
        dropcheck_report[report[0]] = report[1]

    return dropcheck_report


def update_reports(dropcheck_report):
    '''save Dropcheck report to json'''
    if os.path.exists(REPORT_PATH):
        with open(REPORT_PATH, 'r') as f:
            try:
                reports = json.load(f)
            except ValueError:
                reports = {}
    else:
        reports = {}

    reports[time.time()] = dropcheck_report

    with open(REPORT_PATH, 'w') as f:
        json.dump(reports, f)


def main():
    # コンフィグ読み込み
    config = open_config()

    # 実行コマンド群
    tasks = {
        # USB ether
        'ip_info': {
            'command': "networksetup -listallhardwareports | grep -1 USB | sed -n 3p | awk '{print $2}' | xargs -L 1 -I@ ifconfig @ | grep inet | awk '{print $1, $6, \"addr\", $2, $3, $4}'",
            'kind': 'ip_info',
        },
        # airport (for test)
        # 'ip_info': {
        #     'command': "networksetup -listallhardwareports | grep -1 Wi-Fi | sed -n 3p | awk '{print $2}' | xargs -L 1 -I@ ifconfig @ | grep inet | awk '{print $1, $6, \"addr\", $2, $3, $4}'",
        #     'kind': 'ip_info',
        # },
        'ping_gw': {
            'command': 'netstat -rnA -f inet | grep default | awk "{print \$2}" | head -n 1 | xargs -L 1 -I@ ping @ -c 5 -D -s 1472 | grep -1 transmitted',
            'kind': 'ping',
        },
        'ping6_gw': {
            'command': 'netstat -rnA -f inet6 | grep default | awk "{print \$2}" | head -n 1 | xargs -L 1 -I@ ping6 @ -c 5 -Dm -s 1452 | grep -1 transmitted',
            'kind': 'ping',
        },
        'ping_out': {
            'command': 'ping 1.1.1.1 -c 5 -D -s 1472 | grep -1 transmitted',
            'kind': 'ping',
        },
        'ping6_out': {
            'command': 'ping6 2001:200:dff:fff1:216:3eff:feb1:44d7 -c 5 -Dm -s 1452 | grep -1 transmitted',
            'kind': 'ping',
        },
        'dns_v4': {
            'command': f'dig www.wide.ad.jp A @{config["address"]["dns_v4_prime"]} +short',
            'kind': 'dns',
        },
        'dns_v6': {
            'command': f'dig www.wide.ad.jp AAAA @{config["address"]["dns_v6_prime"]} +short',
            'kind': 'dns',
        },
        # 'dns_v6': {
        #     'command': f'dig www.wide.ad.jp AAAA @{config["address"]["dns_v4_prime"]} +short',
        # },
        'trace_v4': {
            'command': 'mtr -c 100 -i 0.1 -wb --report --json 1.1.1.1',
            'kind': 'trace',
        },
        'trace_v6': {
            'command': 'mtr -c 100 -i 0.1 -wb --report --json 2001:200:dff:fff1:216:3eff:feb1:44d7',
            'kind': 'trace',
        },
        'http_v4': {
            'command': 'curl -s https://ipv4.google.com/ -o /dev/null -w "%{http_code}"',
            'kind': 'http',
        },
        'http_v6': {
            'command': 'curl -s https://ipv6.google.com/ -o /dev/null -w "%{http_code}"',
            'kind': 'http',
        }
    }

    # Dropcheckレポートを作成
    dropcheck_report = dropcheck(tasks)

    # 結果をjsonファイルに出力
    update_reports(dropcheck_report)


if __name__ == '__main__':
    main()
