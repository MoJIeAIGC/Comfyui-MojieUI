<script setup lang="ts">
import {t} from "@/messages/i18n";
import {useTransitionStore} from "@/store/transition-store";
import {computed} from "vue";


const options = computed(()=>[
  {
    label: t("Fade"),
    value: "fade"
  },
  {
    label: t("Slide"),
    value: "slide"
  },
  {
    label: t("Zoom"),
    value: "zoom"
  }, {
    label: t("SlideBottom"),
    value: "bottom"
  }, {
    label: t("Rotate"),
    value: "rotate"
  }
])


const store = useTransitionStore()

const enable = computed({
  get() {
    return store.enable
  },
  set(value) {
    store.setEnable(value)
  }
})

const type = computed({
  get() {
    return store.type
  },
  set(value) {
    store.setType(value)
  }
})

</script>

<template>
  <div>

    <el-divider>
      {{ $t("Transition") }}
    </el-divider>
    <el-alert>{{ $t('TransitionDesc') }}</el-alert>
    <div class="flex justify-between">
      <div>
        {{ $t("Enable transition") }}
      </div>
      <div>
        <el-switch v-model="enable"/>
      </div>
    </div>
    <div class="flex justify-between mt-10">
      <div>{{ $t("Transition type") }}</div>
      <div style="width: 100px;">
        <el-select v-model="type" placeholder="请选择" size="small">
          <el-option
              v-for="item in options"
              :key="item.value"
              :label="item.label"
              :value="item.value"
          />
        </el-select>
      </div>
    </div>

  </div>
</template>

<style scoped>

</style>