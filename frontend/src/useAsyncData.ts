import { useState, useEffect } from "react";


export function useAsyncData<T>(url: string, initalState: T, lastFetchTime: number = 0): [T, string, boolean] {
    const [data, setData] = useState(initalState);
    const [error, setError] = useState("");
    const [isLoading, setIsLoading] = useState(true);

    // https://react.dev/learn/you-might-not-need-an-effect#fetching-data
    useEffect(() => {
        let ignore = false;

        setData(initalState)
        setIsLoading(true);
        setError("");

        fetch(url)
            .then(response => {
                return response.json();
            })
            .then(json => {
                if (!ignore) {
                    setData(json);
                    setIsLoading(false);
                } else {
                    console.log(`Ignored response: ${JSON.stringify(json)}`)
                }
            })
            .catch(e => {
                console.error(e.message);
                setError(e.message);
                setIsLoading(false);
            });

        return () => {
            ignore = true;
        };
    }, [url, lastFetchTime]);

    return [data, error, isLoading];
}
