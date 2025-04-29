from flask import Flask, render_template, request, jsonify 
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import io
import base64
import logging
import os
import sys

app = Flask(__name__)

logging.basicConfig(level=logging.DEBUG)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(BASE_DIR, 'fonts', 'Pretendard-Regular.ttf')

# 서버 시작할 때 폰트 존재 여부 확인
# word cloud와 pie chart에 반드시 필요함!
if not os.path.exists(FONT_PATH):
    logging.error(f"❌ 폰트 파일이 {FONT_PATH} 에 없습니다. 서버 종료합니다.")
    sys.exit(1)  # 폰트 없으면 서버를 아예 죽여버림

# word cloud 생성
def generate_wordcloud(text):
    if not text:
        return ""
    try:
        wordcloud = WordCloud(
            width=800,
            height=400,
            background_color='white',
            font_path=FONT_PATH,
            max_words=100,
            collocations=False
        ).generate(text)
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.imshow(wordcloud, interpolation='bilinear')
        ax.axis('off')
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        img_str = 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode('utf-8')
        plt.close()
        return img_str
    except Exception as e:
        logging.error(f"WordCloud generation failed: {e}")
        return ""

# 감정 분석
def analyze_sentiment(text):
    try:
        analyzer = SentimentIntensityAnalyzer()
        score = analyzer.polarity_scores(text)
        if score['compound'] >= 0.05:
            return '긍정'
        elif score['compound'] <= -0.05:
            return '부정'
        else:
            return '중립'
    except Exception as e:
        logging.error(f"Sentiment analysis failed: {e}")
        return '중립'

# 감정 분석 결과 -> Pi Chart 만들기
def generate_sentiment_pie_chart(sentiment_counts):
    try:
        labels = ['긍정', '부정', '중립']
        sizes = [
            sentiment_counts.get('긍정', 0),
            sentiment_counts.get('부정', 0),
            sentiment_counts.get('중립', 0)
        ]
        colors = ['#4CAF50', '#F44336', '#03A9F4']
        explode = (0, 0, 0)

        non_zero_labels = [label for label, size in zip(labels, sizes) if size > 0]
        non_zero_sizes = [size for size in sizes if size > 0]
        non_zero_colors = [color for color, size in zip(colors, sizes) if size > 0]

        if not non_zero_sizes:
            return ""

        # matplot 한글 폰트 설정
        font_prop = FontProperties(fname=FONT_PATH)

        fig, ax = plt.subplots(figsize=(6, 6))
        ax.pie(
            non_zero_sizes,
            labels=non_zero_labels,
            colors=non_zero_colors,
            autopct='%1.1f%%',
            startangle=90,
            textprops={'fontproperties': font_prop, 'fontsize': 12, 'weight': 'bold'}
        )
        ax.axis('equal')
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        img_str = 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode('utf-8')
        plt.close()
        return img_str
    except Exception as e:
        logging.error(f"Pie chart generation failed: {e}")
        return ""

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
# 네이버 뉴스 크롤링
def search():
    keyword = request.form.get('keyword')
    if not keyword:
        return jsonify({'error': '키워드를 입력해주세요.'}), 400

    # 한글 폰트 파일 확인
    if not os.path.exists(FONT_PATH):
        logging.error(f"Font file not found at: {FONT_PATH}")
        return jsonify({'error': '서버에 한국어 폰트가 없습니다. 관리자에게 문의하세요.'}), 500

    today = datetime.today()
    all_articles = []
    all_text = ""

    for i in range(3):  # 최근 2일
        day = today - timedelta(days=i)
        date_str = day.strftime('%Y%m%d')
        logging.debug(f"Searching for keyword: {keyword}, date: {date_str}")

        for start in range(1, 100, 10):  # 10개씩 10 페이지 -> 100개
            try:
                url = (
                    f"https://search.naver.com/search.naver?where=news&query={keyword}"
                    f"&ds={date_str}&de={date_str}&nso=so:r,p:from{date_str}to{date_str},a:all"
                    f"&start={start}"
                )
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                articles = soup.select('.sds-comps-text.sds-comps-text-ellipsis-1.sds-comps-text-type-headline1')

                logging.debug(f"Found {len(articles)} articles for {date_str}, page {start}")
                for article in articles:
                    text = article.get_text().strip()
                    if text:
                        all_articles.append((date_str, text))
                        all_text += text + " "
            except Exception as e:
                logging.error(f"Error during scraping for {date_str}, page {start}: {e}")
                continue

    if not all_articles:
        return jsonify({'error': '검색 결과가 없습니다. 다른 키워드나 날짜를 시도해보세요.'}), 404

    # word cloud 만들기
    wordcloud_url = generate_wordcloud(all_text)

    # 감정 분석
    sentiment_counts = {'긍정': 0, '부정': 0, '중립': 0}
    for _, text in all_articles:
        sentiment = analyze_sentiment(text)
        sentiment_counts[sentiment] += 1

    # 감정 분석 파이 차트 만들기
    sentiment_chart_url = generate_sentiment_pie_chart(sentiment_counts)

    return jsonify({
        'articles': all_articles,
        'wordcloud': wordcloud_url,
        'sentiment_chart': sentiment_chart_url
    })

if __name__ == '__main__':
    app.run(debug=True)