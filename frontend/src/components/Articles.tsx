
import BackendAPI from "../utils/backend-api"
import { useAsyncData } from '../hooks/useAsyncData'


// MARK: - Types

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

type WikiAPIError = {
    url: string;
    message: number;
};

type MostReadArticlesResults = BackendAPI.FetchResults<MostReadArticleData, WikiAPIError>


export type ArticlesParams = {
    backendHost: string;
    languageCode: string;
    startDate: string;
    endDate: string;
    lastFetchTime: number;  // Used to allow component refresh for the URI parameters.
};


// MARK: - Components

export function Articles({ params, onRetryBackendHost }: {
    params: ArticlesParams,
    onRetryBackendHost: () => void,
}) {
    const url = BackendAPI.buildMostReadArticlesURL(params.backendHost, {
        lang_code: params.languageCode,
        start: params.startDate,
        end: params.endDate
    });

    const initialResults: MostReadArticlesResults = { data: [], errors: [] }

    const [results, responseError, isLoading] = useAsyncData(url ?? '', initialResults, params.lastFetchTime);

    const error = BackendAPI.computeFetchErrorType(url, responseError, results);

    const fetchStatusPanel = (
        <div className={"my-4 text-center alert " + (error !== null ? "alert-danger" : "alert-secondary")}>
            {error ? FetchErrorMessage({ error, onRetryBackendHost }) : ''}

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

    const articlesResults = (
        <div>
            {results.errors ? WikipediaAPIErrors({ errors: results.errors }) : ''}

            {!error && results.data ? ArticlesTable({ articles: results.data }) : ''}
        </div>
    );

    return (
        <>
            {!isLoading && fetchStatusPanel}

            {isLoading
                ? loadingMessage
                : articlesResults}
        </>
    )
}


function FetchErrorMessage({ error, onRetryBackendHost }: {
    error: BackendAPI.FetchError,
    onRetryBackendHost: () => void,
}) {
    const retryButton = (
        <button className="ms-3 btn btn-secondary" onClick={onRetryBackendHost}>
            Retry with default server
        </button>
    );

    return (
        <div className="my-1 fs-5">
            <strong>Error: </strong>

            {error.message}

            {error?.errorType == BackendAPI.FetchErrorType.URL && retryButton}
        </div>
    );
}

function WikipediaAPIErrors({ errors }: {
    errors: WikiAPIError[]
}) {
    const resultsErrorsItems = errors.map(error => {
        return (
            <li key={error.url}>
                <a href={error.url} target="_blank" rel="noopener noreferrer">{error.url}</a>
                <span> - </span>
                {error.message}
            </li>
        )
    });

    const resultErrorsPanel = (
        <div className="alert alert-warning">
            <small>
                <h6>Wikipedia API Errors</h6>

                <ul>
                    {resultsErrorsItems}
                </ul>
            </small>
        </div>
    );

    return (errors.length > 0 ? resultErrorsPanel : '')
}


function ArticlesTable({ articles }: {
    articles: MostReadArticleData[],
}) {
    const rows = articles.map((article, index) => ArticleRow({ article, rowNumber: index + 1 }));

    const table = (
        <table className="table">
            <thead>
                <tr>
                    <th scope="col">#</th>
                    <th scope="col">Total Views</th>
                    <th scope="col">URL</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
    );

    const emptyResultsMessage = (
        <h6 className="text-center">
            No results found during this date range.
        </h6>
    );

    return (
        <>
            {articles.length > 0
                ? table
                : emptyResultsMessage}
        </>
    );
}


function ArticleRow({ article, rowNumber }: {
    article: MostReadArticleData,
    rowNumber: number,
}) {
    const numberFormatter = new Intl.NumberFormat();

    return (
        <tr key={article.pageid}>
            <th scope="row">{rowNumber}</th>
            <td>{numberFormatter.format(article.total_views)}</td>
            <td>
                <a href={article.page} target="_blank" rel="noopener noreferrer">{article.page}</a>
            </td>
        </tr>
    );
}
