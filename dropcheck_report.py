# -*- coding:utf-8 -*-

import subprocess
import threading
import time
import os

import json
import yaml


CONFIG_PATH = 'config.yaml'
REPORT_PATH = 'dat/dropcheck_report.json'
LOCK = threading.Lock()


def open_config():
    '''Get DNS address from config'''
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r') as f:
            try:
                config = yaml.load(f)
            except ValueError:
                config = { 'address': {'dns_v4_prime': '1.1.1.1', 'dns_v4_second': '1.0.0.1', 'dns_v6_prime': '2606:4700:4700::1111', 'dns_v6_second': '2606:4700:4700::1001'}}
    else:
        config = { 'address': {'dns_v4_prime': '1.1.1.1', 'dns_v4_second': '1.0.0.1', 'dns_v6_prime': '2606:4700:4700::1111', 'dns_v6_second': '2606:4700:4700::1001'}}

    return config

def get_ip_info(task):
    '''Get IP information with ifconfig'''
    # スペース区切りでifconfigの結果を取得
    ifconfig_rslt = subprocess.check_output(task, shell=True).decode('utf-8')

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

    return ip_info


def get_ping(task):
    '''ping and ping6'''
    ping_rslt = subprocess.check_output(task, shell=True).decode('utf-8')

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

    return(ping_out)


def get_dns(task):
    '''name resolve with dig'''
    dig_rslt = subprocess.check_output(task, shell=True).decode('utf-8')

    dns = {'server': task.split()[3].lstrip('@'), 'result': dig_rslt.rstrip('\n')}

    return(dns)



def get_trace(task, family):
    '''traceroute (sudoしてね)'''
    trace_rslt = subprocess.check_output(task, shell=True).decode('utf-8')

    trace = {family: json.loads(trace_rslt)}

    return(trace)


def dropcheck(tasks):
    # 全タスクを並列処理
#     for task in tasks:
#     tasks_thread = (task)

    dropcheck_report = {}

    dropcheck_report['ip_info'] = get_ip_info(tasks['ip_info'])
    dropcheck_report['ping_gw'] = get_ping(tasks['ping_gw'])
    dropcheck_report['ping6_gw'] = get_ping(tasks['ping6_gw'])
    dropcheck_report['ping_out'] = get_ping(tasks['ping_out'])
    dropcheck_report['ping6_out'] = get_ping(tasks['ping6_out'])
    dropcheck_report['dns_v4'] = get_dns(tasks['dns_v4'])
    dropcheck_report['dns_v6'] = get_dns(tasks['dns_v6'])
    dropcheck_report['trace_v4'] = get_trace(tasks['trace_v4'], 'inet')
    dropcheck_report['trace_v6'] = get_trace(tasks['trace_v6'], 'inet6')

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
        'ip_info': "networksetup -listallhardwareports | grep -1 USB | sed -n 3p | awk '{print \$2}' | xargs -L 1 -I@ ifconfig @ | grep inet | awk '{print $1, $6, \"addr\", $2, $3, $4}'",
        'ping_gw': 'netstat -rnA -f inet | grep default | awk "{print \$2}" | head -n 1 | xargs -L 1 -I@ ping @ -c 5 -D -s 1472 | grep -1 transmitted',
        'ping6_gw': 'netstat -rnA -f inet6 | grep default | awk "{print \$2}" | head -n 1 | xargs -L 1 -I@ ping6 @ -c 5 -Dm -s 1452 | grep -1 transmitted',
        'ping_out': 'ping 1.1.1.1 -c 5 -D -s 1472 | grep -1 transmitted',
        'ping6_out': 'ping6 2606:4700:4700::1111 -c 5 -Dm -s 1452 | grep -1 transmitted',
        'dns_v4': f'dig www.wide.ad.jp A @{config["address"]["dns_v4_prime"]} +short',
        'dns_v6': f'dig www.wide.ad.jp AAAA @{config["address"]["dns_v6_prime"]} +short',
        # 'dns_v6': f'dig www.wide.ad.jp AAAA @{config["address"]["dns_v4_prime"]} +short',
        'trace_v4': 'mtr -c 100 -i 0.1 -wb --report --json 1.1.1.1',
        'trace_v6': 'mtr -c 100 -i 0.1 -wb --report --json 2606:4700:4700::1111',
        'http_v4': 'wget --spider -nv --timeout 60 -t 1 http://ipv4.google.com/ 2>&1',
        'http_v6': 'wget --spider -nv --timeout 60 -t 1 http://ipv6.google.com/ 2>&1',
    }

    # Dropcheckレポートを作成
    dropcheck_report = dropcheck(tasks)

    # 結果をjsonファイルに出力
    update_reports(dropcheck_report)


if __name__ == '__main__':
    main()
