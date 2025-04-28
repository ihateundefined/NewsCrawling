async function performSearch() {
    const keyword = document.getElementById('keyword').value.trim();
    const error = document.getElementById('error');
    const results = document.getElementById('results');
    const loading = document.getElementById('loading');

    if (!keyword) {
      error.textContent = '키워드를 입력해주세요.';
      error.classList.remove('hidden');
      return;
    }

    error.classList.add('hidden');
    results.classList.add('hidden');
    loading.classList.remove('hidden');

    try {
      const response = await fetch('/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `keyword=${encodeURIComponent(keyword)}`
      });

      const data = await response.json();

      if (!response.ok) {
        error.textContent = data.error || '데이터를 가져오는 중 오류가 발생했습니다.';
        error.classList.remove('hidden');
        return;
      }

      // 검색 기록 초기화
      const articlesList = document.getElementById('articles');
      articlesList.innerHTML = '';

      // 신문 기사 검색 결과
      if (data.articles && data.articles.length > 0) {
        data.articles.forEach(([date, text]) => {
          const li = document.createElement('li');
          li.innerHTML = `<span class="text-gray-500">[${date}]</span> ${text}`;
          articlesList.appendChild(li);
        });
      } else {
        articlesList.innerHTML = '<li class="text-gray-500">검색된 기사가 없습니다.</li>';
      }

      // word cloud 결과 보이기
      const wordcloudImg = document.getElementById('wordcloud');
      wordcloudImg.src = data.wordcloud || 'data:image/png;base64,';

      // 감정 분석 결과 보이기
      document.getElementById('positive').textContent = data.sentiment['긍정'] || 0;
      document.getElementById('negative').textContent = data.sentiment['부정'] || 0;
      document.getElementById('neutral').textContent = data.sentiment['중립'] || 0;

      results.classList.remove('hidden');
    } catch (err) {
      error.textContent = '데이터를 가져오는 중 오류가 발생했습니다.';
      error.classList.remove('hidden');
      console.error(err);
    } finally {
      loading.classList.add('hidden');
    }
  }

document.getElementById('search-btn').addEventListener('click', performSearch);

document.getElementById('keyword').addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
        event.preventDefault();
        performSearch();
    }
});