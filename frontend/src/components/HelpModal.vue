<script setup lang="ts">
    interface Props {
        visible: boolean
    }

    defineProps<Props>()
    const emit = defineEmits<{
        close: []
    }>()

    const guides = [
        {
            title: 'Шаг 1: Создание проекта',
            description: 'Нажмите кнопку "+ Добавить проект" в левой панели. Введите название для вашего проекта и нажмите галочку для подтверждения.',
            image: 'guide_1.png',
        },
        {
            title: 'Шаг 2: Добавление треков',
            description: 'После создания проекта нажмите "Добавить файл" в центральной панели. Выберите аудиофайл с вашего компьютера, укажите инструмент (гитара, пианино, вокал) и жанр музыки.',
            image: 'guide_2.png',
        },
        {
            title: 'Шаг 3: Загрузка и обработка',
            description: 'После выбора файла нажмите "Обработать файл". Приложение загрузит файл на сервер и начнёт его обработку. Вы увидите модальное окно с индикатором загрузки.',
            image: 'guide_3.png',
        },
        {
            title: 'Шаг 4: Управление треками',
            description: 'В карточке трека вы можете слушать аудио, регулировать громкость, ставить на паузу и скачивать файл. Используйте ползунок для перемотки по времени.',
            image: 'guide_4.png',
        },
        {
            title: 'Шаг 5: Обработанные результаты',
            description: 'После обработки трек автоматически переместится в правую панель "Обработанный проект". Там вы сможете просмотреть и скачать обработанные версии треков.',
            image: 'guide_5.png',
        },
        {
            title: 'Шаг 6: Сохранение проекта',
            description: 'Когда вы готовы сохранить результаты, нажмите "Сохранить проект" в правой панели. Все обработанные треки загрузятся на ваш компьютер в виде ZIP-архива.',
            image: 'guide_6.png',
        },
    ]
</script>

<template>
    <transition name="modal-fade">
        <div v-if="visible" class="help-overlay" @click="emit('close')">
            <div class="help-modal" @click.stop>
                <button class="btn-close" @click="emit('close')">✕</button>
                <h2 class="modal-title">Справка: Как пользоваться SONARA AI</h2>

                <div class="guides-container">
                    <div v-for="(guide, index) in guides" :key="index" class="guide-card">
                        <div class="guide-number">{{ index + 1 }}</div>
                        <div class="guide-content">
                            <h3 class="guide-title">{{ guide.title }}</h3>
                            <p class="guide-description">{{ guide.description }}</p>
                        </div>
                        <div class="guide-image">
                            <img :src="`/${guide.image}`" :alt="guide.title" />
                        </div>
                    </div>
                </div>

                <div class="help-footer">
                    <p class="help-tip"><strong>Совет:</strong> Вы можете работать с несколькими проектами одновременно. Просто выберите нужный проект в левой панели, и содержимое центральной и правой панелей обновится.</p>
                </div>
            </div>
        </div>
    </transition>
</template>

<style scoped>
    .help-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-color: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 200;
        padding: 20px;
    }

    .help-modal {
        background-color: #ffffff;
        border-radius: 16px;
        padding: 40px;
        max-width: 900px;
        width: 100%;
        max-height: 90vh;
        overflow-y: auto;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
        position: relative;
    }

    .btn-close {
        position: absolute;
        top: 20px;
        right: 20px;
        background: none;
        border: none;
        font-size: 28px;
        cursor: pointer;
        color: #807e82;
        opacity: 0.6;
        transition: opacity 0.2s;
    }

        .btn-close:hover {
            opacity: 1;
        }

    .modal-title {
        margin: 0 0 32px 0;
        font-size: 28px;
        font-weight: 700;
        color: #1e1e1e;
        text-align: center;
    }

    .guides-container {
        display: flex;
        flex-direction: column;
        gap: 32px;
        margin-bottom: 32px;
    }

    .guide-card {
        display: flex;
        gap: 24px;
        padding: 24px;
        background-color: #f5f5f5;
        border-radius: 12px;
        border-left: 4px solid #81679e;
        transition: transform 0.2s;
    }

        .guide-card:hover {
            transform: translateX(4px);
            background-color: #f0f0f0;
        }

    .guide-number {
        min-width: 48px;
        width: 48px;
        height: 48px;
        border-radius: 50%;
        background-color: #81679e;
        color: #ffffff;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
        font-weight: 700;
        flex-shrink: 0;
    }

    .guide-content {
        flex: 1;
        min-width: 0;
    }

    .guide-title {
        margin: 0 0 8px 0;
        font-size: 18px;
        font-weight: 600;
        color: #1e1e1e;
    }

    .guide-description {
        margin: 0;
        font-size: 14px;
        color: #6a696c;
        line-height: 1.6;
    }

    .guide-image {
        min-width: 200px;
        width: 200px;
        height: 150px;
        flex-shrink: 0;
        background-color: #e8e8e8;
        border-radius: 8px;
        overflow: hidden;
        display: flex;
        align-items: center;
        justify-content: center;
    }

        .guide-image img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            object-position: center;
        }

    .help-footer {
        background-color: #ada0bc20;
        padding: 20px;
        border-radius: 8px;
        border-left: 4px solid #ada0bc;
    }

    .help-tip {
        margin: 0;
        font-size: 14px;
        color: #1e1e1e;
        line-height: 1.6;
    }

        .help-tip strong {
            color: #81679e;
        }

    /* Scrollbar styling */
    .help-modal::-webkit-scrollbar {
        width: 8px;
    }

    .help-modal::-webkit-scrollbar-track {
        background: transparent;
    }

    .help-modal::-webkit-scrollbar-thumb {
        background: #807e82;
        border-radius: 4px;
    }

        .help-modal::-webkit-scrollbar-thumb:hover {
            background: #6a696c;
        }

    /* Modal fade transition */
    .modal-fade-enter-active,
    .modal-fade-leave-active {
        transition: opacity 0.3s ease;
    }

    .modal-fade-enter-from,
    .modal-fade-leave-to {
        opacity: 0;
    }

    /* Responsive */
    @media (max-width: 768px) {
        .help-modal {
            padding: 24px;
        }

        .modal-title {
            font-size: 20px;
            margin-bottom: 24px;
        }

        .guide-card {
            flex-direction: column;
            gap: 16px;
        }

        .guide-image {
            min-width: 100%;
            width: 100%;
            height: 200px;
        }

        .guides-container {
            gap: 20px;
        }
    }
</style>
