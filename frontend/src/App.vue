<template>

<div class="layout">


    <!-- 左侧菜单 -->

    <aside class="sidebar">


        <h2>
            🤖 AI助手
        </h2>


        <div
        class="menu"
        :class="{active:page==='chat'}"
        @click="page='chat'"
        >

            💬 AI聊天

        </div>



        <div
        class="menu"
        :class="{active:page==='knowledge'}"
        @click="page='knowledge'"
        >

            📚 知识库管理

        </div>


    </aside>



    <!-- 右侧内容 -->

    <main class="content">


        <ChatBox
        v-if="page==='chat'"
        />


        <Knowledge
        v-if="page==='knowledge'"
        />


    </main>


</div>


</template>



<script setup>

import {
    ref
}
from "vue"



import ChatBox from "./components/ChatBox.vue"

import Knowledge from "./views/Knowledge.vue"



const page = ref("chat")


</script>



<style scoped>


.layout{

    display:flex;

    height:100vh;

    background:#f5f7fa;

}


/* 左侧 */

.sidebar{

    width:220px;

    background:#1f2937;

    color:white;

    padding:25px 15px;

}



.sidebar h2{

    text-align:center;

    margin-bottom:40px;

}



.menu{

    padding:15px;

    margin-bottom:10px;

    border-radius:8px;

    cursor:pointer;

    color:#ddd;

}



.menu:hover{

    background:#374151;

}



.menu.active{

    background:#409eff;

    color:white;

}



/* 右侧 */

.content{

    flex:1;

    overflow:auto;

}



</style>