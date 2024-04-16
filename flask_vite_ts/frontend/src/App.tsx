import { useState, useEffect } from 'react'
import './App.css'

const SERVER_URL = 'http://127.0.0.1:8080'


function App() {
  return (
    <Hello />
  )
}

function Hello() {
  const results = useData('/?name=hello', {data: null});

  return (
      <p>
        <b>Server says:</b> {results.data}
      </p>
  )
}

function useData<T>(uri: string, inital_state: T): T {
  const [data, setData] = useState(inital_state);

  // https://react.dev/learn/you-might-not-need-an-effect#fetching-data
  useEffect(() => {
    let ignore = false;

    fetch(new URL(uri, SERVER_URL))
      .then(response => {
        if (!response.ok) {
          throw new Error('Fetch error response');
        }
        return response.json();
      })
      .then(json => {
        if (!ignore) {
          setData(json);
        }
      })
      .catch(e => {
        console.error(e);
      });

    return () => {
      ignore = true;
    };
  }, [uri]);

  return data;
}


export default App
