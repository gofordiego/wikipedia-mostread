import { useState } from 'react'

import { ArticlesParams, Articles } from './Articles'
import DatePicker from './DatePicker'
import { DEFAULT_BACKEND_HOST, DEFAULT_LANGUAGE_CODE } from '../utils/constants'
import LanguageSelect from './LanguageSelect'
import { useTheme, toggleTheme } from '../hooks/useTheme'
import darkIcon from '../assets/theme-icon-dark.svg'
import lightIcon from '../assets/theme-icon-light.svg'
import '../styles/App.css'


function App() {
  const theme = useTheme();

  const yesterday = new Date(Date.now() - (1000 * 60 * 60 * 24));
  const formattedYesterday = yesterday.toISOString().slice(0, 10);

  const [backendHost, setBackendHost] = useState(DEFAULT_BACKEND_HOST);
  const [languageCode, setLanguageCode] = useState(DEFAULT_LANGUAGE_CODE);
  const [startDate, setStartDate] = useState(formattedYesterday);
  const [endDate, setEndDate] = useState(formattedYesterday);
  const [articlesParams, setArticlesParams] =
    useState<ArticlesParams>({ backendHost, languageCode, startDate, endDate, lastFetchTime: Date.now() });

  function handleLanguageChange(selectedLanguageCode: string) {
    setLanguageCode(selectedLanguageCode);
  }

  function handleStartDateChange(formattedDate: string) {
    setStartDate(formattedDate);
  }

  function handleEndDateChange(formattedDate: string) {
    setEndDate(formattedDate);
  }

  function fetchMostReadArticles(currentHost: string) {
    // 💡 Using `currentHost` parameter to allow `handleRetryDefaultBackendHost` to
    // refresh the Articles component before `setBackendHost` is committed.
    setArticlesParams({ backendHost: currentHost, languageCode, startDate, endDate, lastFetchTime: Date.now() });
  }

  function handleRetryDefaultBackendHost() {
    setBackendHost(DEFAULT_BACKEND_HOST);
    fetchMostReadArticles(DEFAULT_BACKEND_HOST);
  }

  return (
    <>
      <h3 className="my-4 lh-lg text-center">
        Wikipedia - Most Read Articles

        <img className="theme-icon"
          src={theme == 'dark' ? darkIcon : lightIcon}
          onClick={() => toggleTheme(theme)} />
      </h3>

      <div className="app-controllers text-center lh-lg fs-6">
        <small>
          <label>
            <strong>Backend API Server</strong>

            <input type="text" value={backendHost} onChange={e => setBackendHost(e.target.value)} />
          </label>

          <LanguageSelect selectedLanguageCode={languageCode} onLanguageChange={handleLanguageChange} />

          <DatePicker title="Start" formattedDate={startDate} onDateChange={handleStartDateChange} />

          <DatePicker title="End" formattedDate={endDate} onDateChange={handleEndDateChange} />
        </small>

        <button className="btn btn-primary" onClick={() => fetchMostReadArticles(backendHost)}>Fetch</button>
      </div>

      <Articles params={articlesParams} onRetryBackendHost={handleRetryDefaultBackendHost} />
    </>
  )
}


export default App;
