// replaced at build time by HTML template
const errorHtml = __ERROR_HTML__

function handler(event) {
    const request = event.request
    if (request.method !== "GET") {
        return request
    }

    const path = request.uri.split("/")
    if (path.length !== 2) {
        return {
            statusCode: 404,
            headers: { "content-type": { value: "text/html; charset=utf-8" } },
            body: htmlResponse(
                "Invalid path",
                "The path provided is not valid.",
            ),
        }
    }
    const token = path[1]
    if (!/^[A-Za-z0-9]{6}$/.test(token)) {
        return {
            statusCode: 404,
            headers: { "content-type": { value: "text/html; charset=utf-8" } },
            body: htmlResponse(
                "Invalid token",
                "The token provided is not valid.",
            ),
        }
    }
    return request
}

function htmlResponse(title, message) {
    return errorHtml
        .split("${title}")
        .join(title)
        .split("${message}")
        .join(message)
}
