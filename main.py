# coding: utf-8
import datetime
import schedule
import pymysql
import time
import os
import re

from utils import gen_word_cloud_pic
from loguru import logger

# mysql 用户名密码
u = os.getenv("MYSQL_USER")
p = os.getenv("MYSQL_PASSWORD")
# 打开数据库连接
client = pymysql.connect(host="mysql", user=u, passwd=p, port=3306, db="wechat")

# 匹配微信昵称
pattern = r'@([^ | ]+)'

# 获取微信文字聊天记录
def get_message(_gid, _mode):
    _cursor = client.cursor()

    # 默认查询昨天的记录
    _where = "DATE(create_at) = DATE(CURDATE() - INTERVAL 1 DAY)"
    if _mode == 'week':
        # 上周
        _where = "YEARWEEK(date_format(create_at, '%Y-%m-%d')) = YEARWEEK(now()) - 1"
    elif _mode == 'month':
        # 上个月
        _where = "PERIOD_DIFF(date_format(now(), '%Y%m'), date_format(create_at, '%Y%m')) = 1"
    elif _mode == 'year':
        # 去年
        _where = "YEAR(create_at) = YEAR(NOW()) - 1"

    _sql = """
    SELECT
        IF(type = 49,EXTRACTVALUE(content, "/msg/appmsg/title"),content) AS content
    FROM
        `t_message` 
    WHERE
        `from_user` = '{}'
        AND (type = 1 OR (type = 49 AND EXTRACTVALUE (content, "/msg/appmsg/type") = '57'))
        AND {}
    """.format(_gid, _where)

    _cursor.execute(_sql)
    _data = _cursor.fetchall()
    _cursor.close()
    return _data


def gen_word_cloud():
    client.ping(reconnect=True)

    # 查询启用了水群排行榜的群 Id
    _sql = "select wxid from t_friend where (enable_chat_rank IS TRUE or enable_wordcloud IS TRUE) and is_ok IS TRUE"
    _cursor = client.cursor()
    _cursor.execute(_sql)
    _gid = _cursor.fetchall()
    _cursor.close()
    logger.debug("待处理群数量: {}".format(len(_gid)))

    _modes = ['yesterday']  # yesterday | week | month

    _now = datetime.datetime.now()
    # 判断今儿是不是周一
    if _now.weekday() == 0:
        logger.debug("是周一，生成上周的词云数据")
        _modes.append('week')
    # 判断今儿是不是月初
    if _now.day == 1:
        logger.debug("是月初，生成上月的词云数据")
        _modes.append('month')
    # 判断是不是一月一日
    if _now.month == 1 and _now.day == 1:
        logger.debug("是年初，生成去年的词云数据")
        _modes.append('year')

    # 循环生成词云
    for _g in _gid:
        for _mode in _modes:
            _msg = get_message(_g[0], _mode)
            logger.debug("群 {} 模式 {} 消息数量: {}".format(_g[0], _mode, len(_msg)))
            # 如果没消息，跳过处理
            if len(_msg) == 0:
                logger.warning("没有消息，跳过处理")
                continue

            _msgs = ""
            for _i in _msg:
                # 去掉消息体中@的昵称
                _msg_item = re.sub(pattern, '', _i[0])
                if not _msg_item:
                    continue
                _msgs += _msg_item + "\n"
            # 生成词云
            gen_word_cloud_pic(_msgs, _g[0], _mode)

    # 关闭数据库连接
    client.close()

def clean_temp():
    # 清理临时文件
    logger.debug("开始清理临时文件")

    os.system("rm -rf /app/temp/*")
    os.system("rm -rf /app/wordcloud/*")

    logger.success("清理完成")

schedule.every().day.at("00:05").do(clean_temp)
schedule.every().day.at("00:10").do(gen_word_cloud)

while True:
    schedule.run_pending()
    time.sleep(10)