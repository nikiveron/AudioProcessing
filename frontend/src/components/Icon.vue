<script setup lang="ts">
    interface Props {
        name: string
        size?: string | number
        alt?: string
    }

    const props = withDefaults(defineProps<Props>(), {
        size: '24',
    })

    // Маппинг имён иконок на файлы в public
    const iconMap: Record<string, string> = {
        music: 'icon-music.png',
        folder: 'icon-folder.png',
        note: 'icon-note.png',
        notes: 'icon-notes.png',
        'volume-mute': 'icon-mute.png',
        'volume-up': 'icon-volume.png',
        play: 'icon-play.png',
        pause: 'icon-pause.png',
        download: 'icon-download.png',
        trash: 'icon-trash.png',
        edit: 'icon-edit.png',
        check: 'icon-check.png',
        close: 'icon-close.png',
        add: 'icon-add.png',
        headphones: 'icon-headphones.png',
        help: 'icon-help.png',
        mix: 'icon-mix.png',
        AcousticGuitar: 'icon-acousticGuitar.png',
        ElectroGuitar: 'icon-electroGuitar.png',
        Bass: 'icon-bass.png',
        Piano: 'icon-piano.png',
        VocalFemale: 'icon-vocal.png',
        VocalMale: 'icon-vocal.png',
        Kick: 'icon-kick.png',
        Snare: 'icon-snare.png',
        Tom: 'icon-tom.png',
        AltTom: 'icon-tom.png',
        Overhead: 'icon-overhead.png',
    }

    const iconPath = () => {
        const filename = iconMap[props.name] || 'icon-placeholder.png'
        return `/${filename}`
    }
</script>

<template>
    <img :src="iconPath()" :alt="alt || name" :width="size" :height="size" class="icon" />
</template>

<style scoped>
    .icon {
        display: inline-block;
        vertical-align: middle;
        object-fit: contain;
    }
</style>
