<template>
  <AppToast />
    <RouterView />
  <ToastContainer />
</template>

<script setup>
import AppToast from '@/components/ui/AppToast.vue'
import { RouterView } from 'vue-router'
import ToastContainer from '@/components/ui/ToastContainer.vue'
</script>
