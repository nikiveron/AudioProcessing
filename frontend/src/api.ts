import axios from "axios"

const api = axios.create({
    baseURL: "http://localhost:5000/api"
})

export async function getPresignedUpload(filename: string) {
    const res = await api.post("/files/presigned-upload", { filename })
    return res.data
}

export async function createTrack(data: any) {
    const res = await api.post("/tracks", data)
    return res.data
}

export async function startProcess(data: any) {
    const res = await api.post("/process", data)
    return res.data
}