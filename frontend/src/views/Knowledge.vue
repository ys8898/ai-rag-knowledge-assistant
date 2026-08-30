<template>

<div class="knowledge">


    <h2>
        📚 知识库管理
    </h2>


    <!-- 上传 -->

    <div class="upload">


        <input
            type="file"
            @change="selectFile"
        />


        <button
            @click="upload"
        >
            上传文件
        </button>


    </div>



    <!-- 文件列表 -->

    <div class="list">


        <h3>
            当前文件
        </h3>


        <div
            v-for="item in documents"
            :key="item"
            class="file"
        >

            <div>

                <div>
                    📄 {{item.filename}}
                </div>


                <div class="meta">

                    类型:
                    {{item.type}}

                    |

                    大小:
                    {{formatSize(item.size)}}

                    |

                    知识块:
                    {{item.chunks}}

                </div>

            </div>


            <button
                @click="remove(item.filename)"
            >
                删除
            </button>


        </div>


    </div>


</div>


</template>



<script setup>

import {
    ref,
    onMounted
}
from "vue"



import axios from "axios"



const request = axios.create({

    baseURL:
    "/api"

})



// 文件列表

const documents = ref([])



// 当前选择文件

const file = ref(null)



// 获取文件列表

async function loadDocuments(){


    const res =
    await request.get(
        "/documents"
    )


    documents.value =
    res.data


}



// 选择文件

function selectFile(e){


    file.value =
    e.target.files[0]


}



// 上传

async function upload(){


    if(!file.value){

        alert(
            "请选择文件"
        )

        return

    }



    let formData =
    new FormData()



    formData.append(
        "file",
        file.value
    )



    const res =
    await request.post(

        "/upload",

        formData,

        {

            headers:{

                "Content-Type":
                "multipart/form-data"

            }

        }

    )



    alert(
        res.data.message
    )



    //重新加载

    loadDocuments()



}



// 删除

async function remove(filename){


    if(
        !confirm(
            "确定删除?"
        )
    ){

        return

    }



    await request.delete(

        `/documents/${filename}`

    )


    loadDocuments()


}



onMounted(()=>{

    loadDocuments()

})

function formatSize(size){

    if(size < 1024){

        return size + " B"

    }

    if(size < 1024 * 1024){

        return (
            (size / 1024).toFixed(2)
            +
            " KB"
        )

    }


    return (
        (size / 1024 / 1024).toFixed(2)
        +
        " MB"
    )

}

</script>



<style scoped>


.knowledge{

    width:800px;

    margin:50px auto;

}



.upload{

    margin:20px 0;

}



button{

    margin-left:10px;

    padding:6px 15px;

}



.file{

    display:flex;

    justify-content:space-between;

    padding:12px;

    margin-top:10px;

    border:1px solid #ddd;

    border-radius:8px;

}

.meta{

    margin-top:5px;

    font-size:13px;

    color:#888;

}

</style>