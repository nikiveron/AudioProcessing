<script setup lang="ts">
    import { ref, onMounted } from "vue"
    import { getPresignedUpload, createTrack, startProcess } from "./api"
    import { connection, ensureSignalRStarted } from "./signalr"

    const file = ref<File | null>(null)
    const genre = ref("Classic")
    const instrument = ref("Guitar")
    const resultUrl = ref("")
    const loading = ref(false)

    const errorMessage = ref("")

    async function uploadAndProcess() {
        if (!file.value) {
            errorMessage.value = "Please select a file"
            return
        }

        resultUrl.value = ""
        errorMessage.value = ""
        loading.value = true

        try {
            // 1️ Загружаем файл через бекенд → MinIO
            const formData = new FormData()
            formData.append("file", file.value)

            const uploadResponse = await fetch("http://localhost:5000/api/files/upload", {
                method: "POST",
                body: formData
            })

            if (!uploadResponse.ok) {
                throw new Error(`Upload failed with status ${uploadResponse.status}`)
            }

            const uploadResult = await uploadResponse.json()
            console.log("File uploaded:", uploadResult)

            // 2️ Создаём Track в БД
            const track = await createTrack({
                filename: file.value.name,
                inputKey: uploadResult.inputKey,
                outputKey: uploadResult.outputKey
            })

            console.log("Track saved in DB:", track)

            // 3️ Подписка на SignalR
            await ensureSignalRStarted()
            await connection.invoke("SubscribeToJob", track.outputKey)

            // 4️ Маппинг enum → числа
            const genreEnumMap: Record<string, number> = { Classic: 0, Jazz: 1, Rock: 2 }
            const instrumentEnumMap: Record<string, number> = { Guitar: 0, Piano: 1, Vocal: 2 }

            // 5 Запуск обработки
            const processResult = await startProcess({
                trackId: track.trackId,  
                genre: genreEnumMap[genre.value],
                instrument: instrumentEnumMap[instrument.value]
            })

            console.log("Process started:", processResult)

        } catch (error) {
            console.error("Error:", error)
            errorMessage.value = error instanceof Error ? error.message : "Unknown error"
            loading.value = false
        }
    }

    function onFileSelected(event: Event) {
        const target = event.target as HTMLInputElement
        const selectedFile = target.files?.[0] ?? null

        file.value = selectedFile

        resultUrl.value = ""
        errorMessage.value = ""

        loading.value = false
    }

    onMounted(async () => {
        await ensureSignalRStarted()

        connection.on("JobFinished", (msg) => {
            console.log("Job finished event:", msg)
            resultUrl.value = `http://localhost:5000/api/files/download?objectKey=${encodeURIComponent(msg.outputKey)}`
            loading.value = false
        })
    })
</script>

<template>
    <div class="container">
        <h1>Sonara ~ AI аудио обработчик</h1>

        <input type="file" accept="audio/*" @change="onFileSelected" />

        <select v-model="genre">
            <option value="Classic">Классика</option>
            <option value="Jazz">Джаз</option>
            <option value="Rock">Рок</option>
        </select>

        <select v-model="instrument">
            <option value="Guitar">Гитара</option>
            <option value="Piano">Пианино</option>
            <option value="Vocal">Вокал</option>
        </select>

        <button @click="uploadAndProcess" :disabled="loading">
            {{ loading ? "Обработка..." : "Загрузить и обработать" }}
        </button>

        <div v-if="resultUrl">
            <h3>Результат:</h3>
            <audio :src="resultUrl" controls></audio>
        </div>
    </div>
</template>

<style>
    .container {
        max-width: 600px;
        margin: 40px auto;
        font-family: Arial;
        display: flex;
        flex-direction: column;
        gap: 12px;
    }
</style>