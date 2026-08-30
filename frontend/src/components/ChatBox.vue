<template>

<div class="chat">

    <div class="header">

        🤖 企业知识库助手

        <span>
            在线
        </span>

    </div>

    <div 
        class="messages"
        ref="messagesBox"
        >

        <div
        v-for="(msg,index) in messages"
        :key="index"
        class="message"
        >

            <div 
            :class="['bubble',msg.role]"
            >

                <div class="role">
                    {{msg.role}}
                </div>


                <div 
                class="content"
                v-html="renderMarkdown(msg.content)"
                >
                </div>


                <!-- AI信息 -->
                <div 
                v-if="msg.role==='AI'"
                class="info"
                >

                    <div v-if="msg.confidence">

                        <b>可信度：</b>

                        {{msg.confidence.level}}

                        （{{(msg.confidence.score*100).toFixed(0)}}%）

                    </div>



                    <div 
                    v-if="msg.sources && msg.sources.length"
                    >

                        <h4>
                        📚 参考来源
                        </h4>


                        <div
                        v-for="item in msg.sources"
                        :key="item.chunk_id"
                        class="evidence"
                        >

                            <div>
                            📄 {{item.source}}
                            </div>


                            <div>
                            {{item.text}}
                            </div>


                            <div>
                            匹配分：
                            {{item.score.toFixed(2)}}
                            </div>


                </div>

            </div>


        </div>


    </div>


    </div>


        </div>


        <div class="input-box">


        <textarea

        v-model="question"

        @keydown.enter.prevent="send"

        placeholder="请输入你的问题..."

        rows="1"

        ></textarea>



        <button
        @click="send"
        >

            ➤

        </button>


    </div>


    </div>


</template>


<script setup>

import {
    ref,
    nextTick
} from "vue"

import {chatStream} from "../api/chat"

import MarkdownIt from "markdown-it"


const md = new MarkdownIt()

const question=ref("")

const messages=ref([])

const messagesBox = ref(null)
let timer=null

function scrollToBottom(){

    clearTimeout(timer)

    timer=setTimeout(()=>{

        nextTick(()=>{

            if(messagesBox.value){

                messagesBox.value.scrollTop =
                messagesBox.value.scrollHeight

            }

        })

    },50)

}

function renderMarkdown(text){

    return md.render(text)

}

async function send() {

    if (!question.value)
        return


    let q = question.value


    // 添加用户消息
    messages.value.push({

        role:"用户",

        content:q

    })
    scrollToBottom()

    question.value=""


    // 添加空AI消息

    messages.value.push({

        role:"AI",

        content:""

    })


    const index = messages.value.length - 1


    chatStream(

        q,


        // token

        (text)=>{

            messages.value[index].content += text

            scrollToBottom()

        },


        // metadata

        (meta)=>{


            messages.value[index].sources =
                meta.sources


            messages.value[index].confidence =
                meta.confidence


        }

    )

}


</script>


<style scoped>


.chat{

    width:900px;

    height:100%;

    margin:auto;

    display:flex;

    flex-direction:column;

}

.messages{


    flex:1;


    overflow-y:auto;


    border:none;


    padding:30px;


}


.message{

    margin-bottom:20px;

}



.bubble{

    padding:15px;

    border-radius:12px;

    max-width:70%;

}



.用户{

    margin-left:auto;

    background:#e8f3ff;

}



.AI{

    margin-right:auto;

    background:#f6f6f6;

}



.role{

    font-size:13px;

    color:#666;

    margin-bottom:8px;

}



.content{

    line-height:1.8;

    font-size:16px;

}



.info{

    margin-top:15px;

    padding-top:10px;

    border-top:1px solid #ddd;

}



.evidence{

    margin-top:10px;

    padding:10px;

    background:white;

    border-radius:6px;

    border-left:3px solid #409eff;

}

.content :deep(p){

    margin:10px 0;

}


.content :deep(ul){

    padding-left:25px;

}



.content :deep(code){

    background:#eee;

    padding:2px 5px;

    border-radius:4px;

}



.content :deep(pre){

    background:#272822;

    color:white;

    padding:12px;

    border-radius:8px;

    overflow:auto;

}

.input-box{


    display:flex;

    align-items:flex-end;


    width:800px;


    margin:20px auto;


    padding:12px;


    background:white;


    border-radius:16px;


    box-shadow:
    0 4px 15px rgba(0,0,0,0.08);


}



.input-box textarea{


    flex:1;


    resize:none;


    border:none;


    outline:none;


    font-size:16px;


    line-height:1.6;


    padding:10px;


    max-height:120px;


}



.input-box button{


    width:45px;

    height:45px;


    border-radius:50%;


    border:none;


    background:#409eff;


    color:white;


    font-size:20px;


    cursor:pointer;


}



.input-box button:hover{


    background:#337ecc;


}

.header{


    padding:20px;


    font-size:20px;


    font-weight:bold;


    background:white;


    border-bottom:1px solid #eee;


}



.header span{


    float:right;


    font-size:13px;


    color:#67c23a;


}
</style>