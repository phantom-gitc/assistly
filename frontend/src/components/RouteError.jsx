import { Link, useRouteError } from 'react-router-dom'

export default function RouteError() {
  const error = useRouteError()
  const status = error?.status || error?.statusCode
  const notFound = status === 404
  const unavailable = status >= 500

  return (
    <main className="error-state" role="alert">
      <h1>{notFound ? 'Page not found.' : unavailable ? 'We’re having trouble.' : 'We hit a little snag.'}</h1>
      <p>
        {notFound
          ? 'This page may have moved or no longer exists.'
          : unavailable
            ? 'Something went wrong on our side. Please try again in a moment.'
            : 'We couldn’t load this page. Please try again or return home.'}
      </p>
      <Link className="button button-primary" to="/">Back to home</Link>
    </main>
  )
}
