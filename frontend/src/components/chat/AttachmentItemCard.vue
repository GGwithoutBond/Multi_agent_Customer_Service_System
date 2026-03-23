<script setup lang="ts">
import { computed } from 'vue'
import { NIcon, NTag } from 'naive-ui'
import { CartOutline, DocumentTextOutline, DownloadOutline, ListOutline } from '@vicons/ionicons5'

interface AttachmentItem {
  type: 'image' | 'file' | 'order' | 'product'
  url?: string
  name?: string
  size?: number
  order_id?: string
  status?: string
  product_id?: string
  price?: number
  image?: string
}

const props = withDefaults(
  defineProps<{
    item: AttachmentItem
    mode?: 'message' | 'pending'
    removable?: boolean
  }>(),
  {
    mode: 'message',
    removable: false,
  },
)

const emit = defineEmits<{
  remove: []
  open: [url: string]
}>()

const isMessageMode = computed(() => props.mode === 'message')

const sizeLabel = computed(() => {
  const bytes = props.item.size
  if (!bytes) return ''
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
})

const tagType = computed(() => {
  const status = props.item.status || ''
  if (['delivered', '已签收'].includes(status)) return 'success'
  if (['shipped', '已发货'].includes(status)) return 'info'
  if (['processing', '处理中'].includes(status)) return 'warning'
  if (['pending', '待付款'].includes(status)) return 'error'
  return 'default'
})
</script>

<template>
  <div class="attachment-item" :class="[`mode-${mode}`, `type-${item.type}`]">
    <template v-if="item.type === 'image'">
      <img
        class="attachment-image"
        :src="item.url"
        :alt="item.name || '图片'"
        @click="item.url && emit('open', item.url)"
      />
      <div class="attachment-meta">
        <span class="name">{{ item.name || '图片附件' }}</span>
        <span v-if="sizeLabel">{{ sizeLabel }}</span>
      </div>
    </template>

    <template v-else-if="item.type === 'file'">
      <n-icon class="file-icon" :size="mode === 'message' ? 24 : 20">
        <DocumentTextOutline />
      </n-icon>
      <div class="attachment-meta">
        <span class="name">{{ item.name || '文件附件' }}</span>
        <span>{{ sizeLabel || '未知大小' }}</span>
      </div>
      <a v-if="isMessageMode && item.url" :href="item.url" target="_blank" class="download-link" title="下载附件">
        <n-icon :size="18">
          <DownloadOutline />
        </n-icon>
      </a>
    </template>

    <template v-else-if="item.type === 'order'">
      <n-icon class="file-icon" :size="mode === 'message' ? 22 : 18">
        <ListOutline />
      </n-icon>
      <div class="attachment-meta">
        <span class="name">{{ item.name || '订单' }}</span>
        <span>{{ item.order_id || '-' }}</span>
      </div>
      <n-tag size="small" :type="tagType" round>{{ item.status || '未知状态' }}</n-tag>
    </template>

    <template v-else>
      <n-icon class="file-icon" :size="mode === 'message' ? 22 : 18">
        <CartOutline />
      </n-icon>
      <div class="attachment-meta">
        <span class="name">{{ item.name || '商品' }}</span>
        <span>{{ item.product_id || '-' }}</span>
      </div>
      <span class="price" v-if="item.price">¥{{ item.price }}</span>
    </template>

    <button v-if="removable" type="button" class="remove-btn" @click="emit('remove')">×</button>
  </div>
</template>

<style scoped>
.attachment-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  border-radius: 12px;
  border: 1px solid var(--ds-border);
  background: #fff;
  color: var(--ds-text-primary);
}

.mode-message {
  padding: 10px 12px;
  margin-bottom: 8px;
  min-width: 260px;
}

.mode-pending {
  padding: 9px 10px;
  min-width: 180px;
}

.attachment-image {
  width: 56px;
  height: 56px;
  border-radius: 10px;
  object-fit: cover;
  cursor: pointer;
}

.mode-pending .attachment-image {
  width: 42px;
  height: 42px;
}

.attachment-meta {
  display: flex;
  flex-direction: column;
  min-width: 0;
  gap: 3px;
}

.attachment-meta .name {
  font-size: 13px;
  font-weight: 600;
  color: var(--ds-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 180px;
}

.attachment-meta span {
  font-size: 12px;
  color: var(--ds-text-tertiary);
}

.file-icon {
  color: var(--ds-brand);
}

.download-link {
  margin-left: auto;
  color: var(--ds-text-secondary);
}

.download-link:hover {
  color: var(--ds-brand);
}

.price {
  margin-left: auto;
  font-size: 13px;
  font-weight: 700;
  color: var(--ds-brand);
}

.remove-btn {
  position: absolute;
  right: 6px;
  top: 6px;
  width: 18px;
  height: 18px;
  border-radius: 999px;
  border: none;
  background: rgba(25, 34, 56, 0.08);
  color: var(--ds-error);
  line-height: 1;
  cursor: pointer;
}
</style>
