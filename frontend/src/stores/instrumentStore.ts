import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getInstruments } from '../api'

export const useInstrumentStore = defineStore('instruments', () => {
    const instruments = ref<Record<string, string>>({})
    const isLoading = ref(false)
    const error = ref<string | null>(null)

    async function loadInstruments() {
        if (Object.keys(instruments.value).length > 0) {
            return 
        }

        isLoading.value = true
        error.value = null

        try {
            instruments.value = await getInstruments()
        } catch (err) {
            error.value = err instanceof Error ? err.message : 'Неизвестная ошибка'
            console.error('Failed to load instruments:', err)
        } finally {
            isLoading.value = false
        }
    }

    function getDisplayName(key: string): string {
        return instruments.value[key] || key
    }

    function getOptions() {
        return Object.entries(instruments.value).map(([value, label]) => ({
            value,
            label
        }))
    }

    return {
        instruments,
        isLoading,
        error,
        loadInstruments,
        getDisplayName,
        getOptions
    }
})