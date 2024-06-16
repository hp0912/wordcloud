# coding: utf-8

import codecs
import datetime
import shutil
import imageio
import jieba
import numpy as np
import pandas
from wordcloud import WordCloud, ImageColorGenerator
from PIL import ImageFont, Image, ImageDraw
from loguru import logger


def gen_word_cloud_pic(content, gid, mode):
    """生成词云工具类

    :param
        content: 文字正文
        input_prefix: 生成词云图片文件名
        file_path: 生成词云图片保存路径
    """
    stopwords_filename = 'config/stopwords.txt'
    font_filename = 'config/font/jiangxizhuokai2.0.ttf'
    template_dir = 'config/templates'

    # 加载自定义词典
    jieba.load_userdict('config/userdict.txt')
    # 配置停顿词
    stopwords = set([line.strip()
                     for line in codecs.open(stopwords_filename, 'r', 'utf-8')])

    _seg_list = jieba.cut(content)
    words = []
    for seg in _seg_list:
        word = seg.strip().lower()
        if len(word) > 1 and word not in stopwords:
            words.append(word)

    words_df = pandas.DataFrame({'word': words})
    words_stat = words_df.groupby(by=['word'])['word'].agg(np.size)
    words_stat = words_stat.to_frame()
    words_stat.columns = ['number']
    words_stat = words_stat.reset_index().sort_values(by="number", ascending=False)

    # 保存高频词信息
    # words_stat.to_csv('output/%s_words_stat.txt' % input_prefix, sep='\t', index=False)

    logger.success('[{}]共有 {} 个词(已去重)'.format(gid, len(words_stat)))
    # 如果没得词，跳过处理
    if len(words_stat) == 0:
        return

    # 生成词云图片
    _background_img = imageio.imread(template_dir + '/heart.jpg')
    _word_cloud = WordCloud(font_path=font_filename, background_color='white',
                            mask=_background_img, max_font_size=600, random_state=100)
    _word_cloud = _word_cloud.fit_words(
        dict(words_stat.head(100).itertuples(index=False)))

    _background_img_colors = ImageColorGenerator(_background_img)
    _word_cloud.recolor(color_func=_background_img_colors)

    # 获取当前日期
    _now = datetime.datetime.now()
    _year = _now.year
    _date = ""
    if mode == 'yesterday':
        _date = (_now + datetime.timedelta(days=-1)).strftime("%Y%m%d")
    elif mode == 'week':
        # 取出上周的周数
        _week = _now.isocalendar()
        _date = "{}{}".format(_week[0], _week[1] - 1)
    elif mode == 'month':
        # 获取上个月
        _now = _now.replace(day=1)
        _date = (_now + datetime.timedelta(days=-1)).strftime("%Y%m")
    elif mode == 'year':
        # 去年
        _date = _now.year - 1


    output_filename = "/app/wordcloud/{}_{}.png".format(_date, gid)

    logger.debug('[{}]正在保存文件：{}'.format(gid, output_filename))
    _word_cloud.to_file(output_filename)
    logger.success('[{}]文件保存成功，开始添加头部信息'.format(gid))
    add_title(mode, output_filename)

    # 复制到 resource 目录
    # shutil.copy(output_filename, "/resources/wordcloud/wxid_lhq1k9l9j30n22/2024/{}_{}.png".format(_date, gid))


# 给图片加个头
def add_title(mode, file):
    body_img = Image.open(file)
    width, height = body_img.size
    # 高度增加 100 像素，用来放头部
    height += 100
    # 生成一张尺寸为 width * height  背景色为白色的图片
    bg = Image.new('RGB', (width, height), color=(255, 255, 255))
    # 写入图片主体内容，从 100 像素高度开始写入
    bg.paste(body_img, (0, 100))
    
    # 根据不同模式，生成不同的标题，默认是昨日的日期
    _now = datetime.datetime.now()
    title = (_now + datetime.timedelta(days=-1)).strftime("%Y年%m月%d日")
    if mode == 'week':
        # 取出上周的周数
        _week = _now.isocalendar()
        title = "{}年第{}周".format(_week[0], _week[1] - 1)
    elif mode == 'month':
        # 获取上个月
        _now = _now.replace(day=1)
        title = (_now + datetime.timedelta(days=-1)).strftime("%Y年%m月")
    elif mode == 'year':
        # 获取去年
        _now = _now.replace(day=1)
        title = (_now + datetime.timedelta(days=-1)).strftime("%Y年")
    title = "{} 词云".format(title)
    
    # 设置需要显示的字体
    fontpath = "config/font/jiangxizhuokai2.0.ttf"
    font = ImageFont.truetype(fontpath, 32)
    # 计算出要写入的文字占用的像素
    w, h = font.getsize(title)
    logger.debug("文字宽度: {}  高度: {}".format(w, h))
    # 创建画布
    draw = ImageDraw.Draw(bg)
    # 绘制文字信息
    draw.text(((width - w) / 2, (100 - h) / 2), title, font=font, fill="#ff0000")
    # 保存画布
    bg.save(file, "PNG")
    logger.success("{} 标题添加完成".format(file))
