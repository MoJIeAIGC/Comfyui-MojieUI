<template>
  <div class="error-page">
    <div class="content">
      <h1>404</h1>
      <div class="desc">抱歉，你访问的页面不存在</div>
    </div>
  </div>
</template>

<script>
export default {
  name: "error-404"
};
</script>
<style lang="less" scoped>
.error-page {
  background: #f0f2f5;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  .content {
    text-align: center;
    h1 {
      color: #434e59;
      font-size: 72px;
      font-weight: 600;
      line-height: 72px;
      margin:0 0 24px 0;
    }
    .desc {
      color: rgba(0, 0, 0, 0.45);
      font-size: 20px;
      line-height: 28px;
      margin:0;
    }
  }
}
</style>
