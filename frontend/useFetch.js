import { useEffect, useState } from "react";

export const useFetch = (apiUrl) => {
  const [url, setUrlState] = useState(apiUrl);
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(null);
  const [trigger, setTrigger] = useState(0); // para forzar fetch aunque la url no cambie

  useEffect(() => {
    const controller = new AbortController();
    const fetchData = async () => {
      setIsLoading(true);
      console.log('[useFetch] fetching URL:', url);

      try {
        const response = await fetch(url,{
          signal: controller.signal,
          headers:{
            accept: 'application/json',
            'User-agent': 'learning app',
          }
        });
  const responseData = await response.json();
  console.log('[useFetch] fetched:', { url, success: true });
        setData(responseData);
        setIsLoading(false);
        setHasError(null);
      } catch (error) {
        if (error.name === 'AbortError') return;
        setIsLoading(false);
        setHasError(error);
        console.error('[useFetch] fetch error for', url, error);
      }
    };
    if(url !== ''){
      fetchData();
    }else{
      setIsLoading(false);
      setData(null);
      setHasError(null);
    }
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url, trigger]);

  const forceFetch = () => setTrigger(t => t + 1);

  // wrapper for setUrl: if the new url is equal to the current one, trigger a fetch
  const setUrl = (newUrl) => {
    if (newUrl !== url) setUrlState(newUrl);
  };

  return { data, isLoading, hasError, setUrl, url, forceFetch };
};
