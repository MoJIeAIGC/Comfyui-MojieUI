import {modelMappingLabel} from "@/options/model.js";

export const welcomeList = [
    {
        model: 'gpt-4o-image',
        welcome: '欢迎使用GPT-40-image作图',
        textList: [
            {title: '理解力强', text: 'ChatGPT擅长理解文字，生成图像时能更准确地理解你的想法~'},
            {title: '快速修改', text: '你不满意图片?说一声“换个角度”或“再可爱一点”，我立刻就能再生一个!'},
            {title: '风格灵活', text: '写实的、卡通的、二次元风、复古、极简……你说什么风格我都能切换!'},
            {title: '对话互动', text: '无需反复微调 prompt，可以跟你像聊天一样一步步做图'},
        ],
        operateList: [
            {text: '使用40模型制作产品家具图', path: '/home', sendText: '制作产品家具图',info:{
                    "id": 37,
                    "is_deleted": false,
                    "fromuser": false,
                    "title": "沙发生成场景",
                    "text": "椅子旁放一盏落地灯或一个小边几，打造一个阅读角落，",
                    "image_path": "https://qihuaimage.tos-cn-guangzhou.volces.com/sMsUxJ.jpg",
                    "image_path_res": "https://qihuaimage.tos-cn-guangzhou.volces.com/IJBZsi.jpg",
                    "created_date": "2025-04-19T11:38:13.851312",
                    "category": "",
                    "english_prompt": null,
                    "remarks": "",
                    "generation_method": "GPT4o",
                    "like_count": 0,
                    "is_liked": 0,
                    "tags": [
                        17
                    ],
                    "realtagsname": [],
                    "realtags": []
                }},
            {text: '使用40模型体验生成logo', path: '/home', sendText: '生成logo',info:{
                    "id": 10,
                    "is_deleted": false,
                    "fromuser": false,
                    "title": "两张图元素组合成logo",
                    "text": "将图中两种元素组合到一起，生成一个新的极简logo，并配上中文：熊猫烘焙。",
                    "image_path": "https://qihuaimage.tos-cn-guangzhou.volces.com/cVqHsc.jpg,https://qihuaimage.tos-cn-guangzhou.volces.com/EGO4o6.jpg",
                    "image_path_res": "https://qihuaimage.tos-cn-guangzhou.volces.com/hOwrhk.jpg",
                    "created_date": "2025-04-17T09:55:10.071990",
                    "category": "logo设计",
                    "english_prompt": null,
                    "remarks": "",
                    "generation_method": "GPT4o",
                    "like_count": 0,
                    "is_liked": 0,
                    "tags": [
                        4
                    ],
                    "realtagsname": [],
                    "realtags": []
                }},
            {text: '使用4o模型替换模特服装', path: '/home',info:{
                    "id": 13,
                    "is_deleted": false,
                    "fromuser": false,
                    "title": "替换模特服装",
                    "text": "图1衣服替换到图2模特身上",
                    "image_path": "https://qihuaimage.tos-cn-guangzhou.volces.com/vY1kfr.jpg,https://qihuaimage.tos-cn-guangzhou.volces.com/r49joL.jpg",
                    "image_path_res": "https://qihuaimage.tos-cn-guangzhou.volces.com/8KzPpF.jpg",
                    "created_date": "2025-04-17T10:18:15.049969",
                    "category": "服装",
                    "english_prompt": null,
                    "remarks": "",
                    "generation_method": "GPT4o",
                    "like_count": 0,
                    "is_liked": 0,
                    "tags": [
                        3
                    ],
                    "realtagsname": [],
                    "realtags": []
                }}
        ]
    },
    {
        model: 'gemini',
        welcome: '欢迎使用Gemini作图',
        textList: [
            {title: '快速修改', text: '无论动漫设计，真实摄影，都能很好支持~'},
            {title: '风格灵活', text: '写实的、卡通的、二次元风、复古、极简……你说什么风格我都能切换!'},
            {title: '对话互动', text: '无需反复微调 prompt，可以跟你像聊天一样一步步做图'},
        ],
        operateList: [
            {text: '使用Gemini制作产品家具图', path: '/home'},
            {text: '使用Gemini体验生成logo', path: '/home'},
            {text: '使用Gemini替换模特服装', path: '/home'}
        ]
    },
    {
        model: 'flex',
        welcome: '欢迎使用'+modelMappingLabel.flex+'作图',
        textList: [
            {title: '百变风格', text: '无论动漫设计，真实摄影，都能很好支持~'},
            {title: '提示词', text: '支持中英文提示词'},
            {title: '更多可控', text: '将会添加lora+control支持，可控性更强！'}
        ],
        operateList: [
            {
                text: '使用'+modelMappingLabel.flex+'生成动漫形象', path: '/home', sendText: '动漫形象', info: {
                    "id": 213,
                    "is_deleted": false,
                    "fromuser": false,
                    "title": null,
                    "text": "动画3D，Ludicrous皮卡丘，背景，日落，简单干净，恐怖，三色",
                    "image_path": "",
                    "image_path_res": "https://qihuaimage.tos-cn-guangzhou.volces.com/examples/mjar_00184__20250516163409.png",
                    "created_date": "2025-05-16T16:34:11.023233",
                    "category": null,
                    "english_prompt": null,
                    "remarks": null,
                    "generation_method": "flex",
                    "like_count": 0,
                    "is_liked": 0,
                    "tags": [
                        23
                    ],
                    "realtagsname": [],
                    "realtags": []
                }
            },
            {
                text: '使用'+modelMappingLabel.flex+'生成超现实风格', path: '/home', sendText: '超现实风格', info: {
                    "id": 156,
                    "is_deleted": false,
                    "fromuser": false,
                    "title": null,
                    "text": "作者：Carne Griffiths，肖像，酷儿艺术，女巫特写“启蒙的香气，觉醒的香气，照亮自我发现和内心平静的道路。”，细节艺术，硬光，L USM，电影颗粒",
                    "image_path": "",
                    "image_path_res": "https://qihuaimage.tos-cn-guangzhou.volces.com/examples/mjar_00152__20250516160039.png",
                    "created_date": "2025-05-16T16:00:41.141871",
                    "category": null,
                    "english_prompt": null,
                    "remarks": null,
                    "generation_method": "flex",
                    "like_count": 0,
                    "is_liked": 0,
                    "tags": [
                        22
                    ],
                    "realtagsname": [],
                    "realtags": []
                }
            },
        ]
    },
    {
        model: 'furniture',
        welcome: '欢迎使用室内家具模型作图',
        textList: [
            {title: '快速修改', text: '你不满意图片?说一声“换个角度”或“再可爱一点”，我立刻就能再生一个!'},
            {title: '风格灵活', text: '写实的、卡通的、二次元风、复古、极简……你说什么风格我都能切换!'},
            {title: '对话互动', text: '无需反复微调 prompt，可以跟你像聊天一样一步步做图'},
        ],
        operateList: [
            {text: '使用室内家具模型制作产品家具图', path: '/home', sendText: '超现实风格',info:{}},
            {text: '使用室内家具模型替换模特服装', path: '/home', sendText: '超现实风格',info:{}}
        ]
    },
    {
        model: 'qiHua',
        welcome: '欢迎使用'+modelMappingLabel.qiHua+'作图',
        textList: [
            {title: '精准提示词', text: '对中文理解更强，AI感更少。'},
            {title: '多种风格', text: '尤其擅长制作产品海报，人像摄影'},
            {title: '可输出中文', text: '可精准输出中文，记得使用引号” 将文字标明'},
        ],

        operateList: [
            {text: '使用'+modelMappingLabel.qiHua+'生成质感人像', path: '/home', sendText: '质感人像',info:{
                    "id": 422,
                    "is_deleted": false,
                    "fromuser": true,
                    "title": "女性：穿着黑色长裙，戴着黑色宽边帽，站在铁轨上铁轨：贯穿画面，延伸至远方，浓雾充斥环绕在铁轨和人物周围，主体:穿着黑色长裙的女性色调:以黑色、灰色和红色为主，营造神秘和时尚感风格:神秘、时尚、戏剧化构图:女性站在铁轨中央，面对镜头，一只手拿住帽子遮挡住面部，面向镜头，另一只手自然下垂，浓雾从底部升起，围绕在人物和铁轨周围，迷雾充满整个屏幕，文字位于画面顶部配文:“HOLYMOTHER”，字体:红色无衬线字体，粗体材质:女性的服装为黑色布料，裸肩装，铁轨为金属材质浓雾为虚化效果光线，女性长头发被风吹乱，强烈的黄色光线从女人身后发出，把女性长发发丝和整块迷雾区域照亮，增强神秘感空间结构:前景：女性和铁轨背景：浓雾和远处的桥梁或建筑物文本提示词（AI绘画生成）主题: 神秘时尚海报元素:女性（黑色长裙、黑色宽边帽、站在铁轨上）铁轨（贯穿画面）浓雾（环绕在周围）色调:黑色、灰色、红色风格:神秘、时尚、戏剧化构图:女性居中站在铁轨上，浓雾环绕红色无衬线字体，粗体材质:黑色布料（服装）金属（铁轨）虚化效果（浓雾）光线:低沉光线，增强神秘感空间结构:前景：女性和铁轨背景：浓雾和远处建筑物",
                    "text": "女性：穿着黑色长裙，戴着黑色宽边帽，站在铁轨上铁轨：贯穿画面，延伸至远方，浓雾充斥环绕在铁轨和人物周围，主体:穿着黑色长裙的女性色调:以黑色、灰色和红色为主，营造神秘和时尚感风格:神秘、时尚、戏剧化构图:女性站在铁轨中央，面对镜头，一只手拿住帽子遮挡住面部，面向镜头，另一只手自然下垂，浓雾从底部升起，围绕在人物和铁轨周围，迷雾充满整个屏幕，文字位于画面顶部配文:“HOLYMOTHER”，字体:红色无衬线字体，粗体材质:女性的服装为黑色布料，裸肩装，铁轨为金属材质浓雾为虚化效果光线，女性长头发被风吹乱，强烈的黄色光线从女人身后发出，把女性长发发丝和整块迷雾区域照亮，增强神秘感空间结构:前景：女性和铁轨背景：浓雾和远处的桥梁或建筑物文本提示词（AI绘画生成）主题: 神秘时尚海报元素:女性（黑色长裙、黑色宽边帽、站在铁轨上）铁轨（贯穿画面）浓雾（环绕在周围）色调:黑色、灰色、红色风格:神秘、时尚、戏剧化构图:女性居中站在铁轨上，浓雾环绕红色无衬线字体，粗体材质:黑色布料（服装）金属（铁轨）虚化效果（浓雾）光线:低沉光线，增强神秘感空间结构:前景：女性和铁轨背景：浓雾和远处建筑物",
                    "image_path": "",
                    "image_path_res": "https://qihuaimage.tos-cn-guangzhou.volces.com/volcengine_20250520141342.png",
                    "created_date": "2025-05-20T15:00:11.198742",
                    "category": null,
                    "english_prompt": null,
                    "remarks": null,
                    "generation_method": "dou",
                    "like_count": 0,
                    "is_liked": 0,
                    "tags": [
                        24
                    ],
                    "realtagsname": [],
                    "realtags": []
                }},
            {text: '使用'+modelMappingLabel.qiHua+'生成产品海报', path: '/home', sendText: '产品海报',info:{
                    "id": 421,
                    "is_deleted": false,
                    "fromuser": true,
                    "title": "生成一张美女时尚海报。背景写上\"时尚先锋\"几个字，女士穿着夏季服装。",
                    "text": "生成一张美女时尚海报。背景写上\"时尚先锋\"几个字，女士穿着夏季服装。",
                    "image_path": "",
                    "image_path_res": "https://qihuaimage.tos-cn-guangzhou.volces.com/volcengine_20250515110042.png",
                    "created_date": "2025-05-19T19:13:50.998173",
                    "category": null,
                    "english_prompt": null,
                    "remarks": null,
                    "generation_method": "dou",
                    "like_count": 0,
                    "is_liked": 0,
                    "tags": [
                        42
                    ],
                    "realtagsname": [],
                    "realtags": []
                }}
        ]
    }
]