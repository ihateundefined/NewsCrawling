from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import io
import base64
import logging
import os
import sys

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(BASE_DIR, 'fonts', 'Pretendard-Regular.ttf')

# 서버 시작할 때 폰트 존재 여부 확인
if not os.path.exists(FONT_PATH):
    logging.error(f"❌ 폰트 파일이 {FONT_PATH} 에 없습니다. 서버 종료합니다.")
    sys.exit(1)  # 폰트 없으면 서버를 아예 죽여버림

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
        plt.savefig(buf, format='png')
        buf.seek(0)
        img_str = 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode('utf-8')
        plt.close()
        return img_str
    except Exception as e:
        logging.error(f"WordCloud generation failed: {e}")
        return ""

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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    keyword = request.form.get('keyword')
    if not keyword:
        return jsonify({'error': '키워드를 입력해주세요.'}), 400

    # Check if font file exists
    if not os.path.exists(FONT_PATH):
        logging.error(f"Font file not found at: {FONT_PATH}")
        return jsonify({'error': '서버에 한국어 폰트가 없습니다. 관리자에게 문의하세요.'}), 500

    today = datetime.today()
    all_articles = []
    all_text = ""

    for i in range(2):  # 최근 2일
        day = today - timedelta(days=i)
        date_str = day.strftime('%Y%m%d')
        logging.debug(f"Searching for keyword: {keyword}, date: {date_str}")

        for start in range(1, 100, 10):  # 10 페이지
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

    # Generate word cloud
    wordcloud_url = generate_wordcloud(all_text)

    # Sentiment analysis
    sentiment_counts = {'긍정': 0, '부정': 0, '중립': 0}
    for _, text in all_articles:
        sentiment = analyze_sentiment(text)
        sentiment_counts[sentiment] += 1

    return jsonify({
        'articles': all_articles,
        'wordcloud': wordcloud_url,
        'sentiment': sentiment_counts
    })

if __name__ == '__main__':
    app.run(debug=True)