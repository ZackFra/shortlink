function handler(event) {
    const request = event.request
    if (request.method !== "GET") {
        return request
    }

    const path = request.uri.split("/")
    if (path.length !== 2) {
        return {
            statusCode: 404,
            statusDescription: "Invalid path",
            headers: { "content-type": { value: "application/json" } },
            body: JSON.stringify({
                error: "Invalid path",
                message: "The path provided is not valid.",
            }),
        }
    }
    const token = path[1]
    if (!/^[A-Za-z0-9]{6}$/.test(token)) {
        return {
            statusCode: 404,
            statusDescription: "Invalid token",
            headers: { "content-type": { value: "application/json" } },
            body: JSON.stringify({
                error: "Invalid token",
                message: "The token provided is not valid.",
            }),
        }
    }
    return request
}
