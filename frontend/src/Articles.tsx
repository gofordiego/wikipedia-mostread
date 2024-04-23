
import BackendAPI from "./backend-api"
import { useAsyncData } from './useAsyncData'


export type ArticlesParams = {
    backendHost: string;
    languageCode: string;
    startDate: string;
    endDate: string;
    lastFetchTime: number;  // Used to allow component refresh for the URI parameters.
};


// MostReadArticlesResults types

type ArticleViewHistory = {
    date: string;
    views: number;
};

type MostReadArticleData = {
    page: string;
    pageid: number;
    total_views: number;
    view_history: ArticleViewHistory[];
};

type MostReadArticlesError = {
    url: string;
    message: number;
};

type MostReadArticlesResults = {
    data?: MostReadArticleData[];
    errors?: MostReadArticlesError[];
    request_error?: string;
};


// ArticlesFetchError

enum ArticlesResponseError {
    URL,  // Malformed URL
    Response,  // Non-OK fetch response
    Request,  // Invalid API params (MostReadArticlesResponse.request_error)
}

function computeArticlesResponseError(url: string | undefined, responseError: string, results: MostReadArticlesResults): ArticlesResponseError | null {
    if (url === undefined) {
        return ArticlesResponseError.URL;
    } else if (results.request_error) {
        return ArticlesResponseError.Request;
    } else if (responseError) {
        return ArticlesResponseError.Response;
    } else {
        return null
    }
}


const numberFormatter = new Intl.NumberFormat();


export function Articles({ params, onRetryBackendHost }: {
    params: ArticlesParams,
    onRetryBackendHost: () => void,
}) {
    const url = BackendAPI.buildMostReadArticlesURL(params.backendHost, {
        lang_code: params.languageCode,
        start: params.startDate,
        end: params.endDate
    });

    const emptyResults: MostReadArticlesResults = { data: [], errors: [] }
    const [results, responseError, isLoading] = useAsyncData(url ?? '', emptyResults, params.lastFetchTime);

    const error = computeArticlesResponseError(url, responseError, results);

    const backendHostErrorMessage = (
        <span>
            Invalid Backend API Server

            <button className="ms-3 btn btn-secondary" onClick={onRetryBackendHost}>
                Retry with default server
            </button>
        </span>
    );

    const errorMessage = (
        <div className="my-1 fs-5">
            <strong>Error: </strong>

            {error == ArticlesResponseError.URL && backendHostErrorMessage}

            {error == ArticlesResponseError.Response && responseError}

            {error == ArticlesResponseError.Request && results.request_error}
        </div>
    );

    const articlesRows = results.data?.map((article, index) => {
        return (
            <tr key={article.pageid}>
                <th scope="row">{index + 1}</th>
                <td>{numberFormatter.format(article.total_views)}</td>
                <td>
                    <a href={article.page} target="_blank" rel="noopener noreferrer">{article.page}</a>
                </td>
            </tr>
        )
    }) ?? '';

    const articlesTable = (
        <table className="table">
            <thead>
                <tr>
                    <th scope="col">#</th>
                    <th scope="col">Total Views</th>
                    <th scope="col">URL</th>
                </tr>
            </thead>
            <tbody>
                {articlesRows}
            </tbody>
        </table>
    );

    const resultsErrorsItems = results.errors?.map(error => {
        return (
            <li key={error.url}>
                <a href={error.url} target="_blank" rel="noopener noreferrer">{error.url}</a>
                <span> - </span>
                {error.message}
            </li>
        )
    }) ?? '';

    const resultsErrorsMessage = (
        <div className="alert alert-warning">
            <small>
                <h6>Wikipedia API Errors</h6>

                <ul>
                    {resultsErrorsItems}
                </ul>
            </small>
        </div>
    );

    const emptyResultsMessage = (
        <h6 className="text-center">
            No results found during this date range.
        </h6>
    );

    const articlesResults = (
        <div>
            {resultsErrorsItems.length > 0 && resultsErrorsMessage}

            {articlesRows.length
                ? articlesTable
                : emptyResultsMessage}
        </div>
    );

    const fetchInfo = (
        <div className={"my-4 text-center alert " + (error !== null ? "alert-danger" : "alert-secondary")}>
            {error !== null && errorMessage}

            <small>
                <strong>Backend API URL: </strong>
                <a href={url}>{url}</a>
                <span> {error === null ? "✅" : "❌"}</span>

                <span className="text-nowrap">
                    <strong className="ms-3">Last fetch at: </strong>
                    {new Date(params.lastFetchTime).toISOString()}
                </span>
            </small>
        </div>
    );

    const loadingMessage = (
        <div className="my-5 text-center">
            <div className="spinner-border text-primary" role="status">
                <span className="visually-hidden">Loading...</span>
            </div>
            <h5>
                Fetching most read articles...

            </h5>
            <small>
                This might take while for large date ranges.
            </small>
        </div>
    );

    return (
        <>
            {!isLoading && fetchInfo}

            {isLoading
                ? loadingMessage
                : articlesResults}
        </>
    );
}
