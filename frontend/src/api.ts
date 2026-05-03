import axios, { AxiosError } from "axios"

interface ApiError {
    key: string;
    errorMessage: string;
}

const api = axios.create({
    baseURL: "http://localhost:5000/api"
})

export async function uploadTrack(formData: FormData) {
    try {
        const res = await api.post("/files/upload", formData, {
            headers: {
                'Content-Type': 'multipart/form-data'
            }
        })

        return res.data
    }
    catch (error) {
        if (axios.isAxiosError(error)) {
            const serverError = error as AxiosError<ApiError>

            if (serverError.response) {
                const errors = serverError.response.data as ApiError[]
                const firstError = errors?.[0]

                const message =
                    firstError?.errorMessage
                        ? `Ошибка сервера (${firstError.key}): ${firstError.errorMessage}`
                        : "Ошибка сервера"

                throw new Error(message)
            }

            if (serverError.request) {
                throw new Error("Сервер не отвечает")
            }
        }

        throw new Error("Неожиданная ошибка во время загрузки трека")
    }
}

export async function createTrack(data: any) {
    try {
        const res = await api.post("/tracks", data)

        return res.data
    }
    catch (error) {
        if (axios.isAxiosError(error)) {
            const serverError = error as AxiosError<ApiError>

            if (serverError.response) {
                const errors = serverError.response.data as ApiError[]
                const firstError = errors?.[0]

                const message =
                    firstError?.errorMessage
                        ? `Ошибка сервера (${firstError.key}): ${firstError.errorMessage}`
                        : "Ошибка сервера"

                throw new Error(message)
            }

            if (serverError.request) {
                throw new Error("Сервер не отвечает")
            }
        }

        throw new Error("Неожиданная ошибка во время загрузки трека")
    }
}

export async function startProcess(data: any) {
    try {
        const res = await api.post("/process", data)

        return res.data
    }
    catch (error) {
        if (axios.isAxiosError(error)) {
            const serverError = error as AxiosError<ApiError>

            if (serverError.response) {
                const errors = serverError.response.data as ApiError[]
                const firstError = errors?.[0]

                const message =
                    firstError?.errorMessage
                        ? `Ошибка сервера (${firstError.key}): ${firstError.errorMessage}`
                        : "Ошибка сервера"

                throw new Error(message)
            }

            if (serverError.request) {
                throw new Error("Сервер не отвечает")
            }
        }

        throw new Error("Неожиданная ошибка во время загрузки трека")
    }
}

export async function getInstruments(): Promise<Record<string, string>> {
    try {
        const res = await api.get("/common/instruments")
        return res.data
    } catch (error) {
        if (axios.isAxiosError(error)) {
            const serverError = error as AxiosError<ApiError>

            if (serverError.response) {
                const errors = serverError.response.data as ApiError[]
                const firstError = errors?.[0]

                const message =
                    firstError?.errorMessage
                        ? `Ошибка сервера (${firstError.key}): ${firstError.errorMessage}`
                        : "Ошибка сервера"

                throw new Error(message)
            }

            if (serverError.request) {
                throw new Error("Сервер не отвечает")
            }
        }
        throw new Error("Неожиданная ошибка при загрузке инструментов")
    }
}