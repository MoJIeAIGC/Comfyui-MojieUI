export  const modelMappingLabel = {
    gpt:'原生GPT4o图像生成',
    gptLabel:'GPT40-image',
    qiHua:'奇画T2I&F-kontext',
    flex:'Flux-kontext 综合',
}

export const modelList = [
    {label: modelMappingLabel.gpt, tip: '最强绘图模型,支持图片编辑', value: 'gpt-4o-image', icon: 'icon-GPT1'},
    // {label: 'Gemini-image', tip: '家具家装设计,对中式把握更好', value: 'gemini'},
    {label: modelMappingLabel.flex, tip: '效果堪比MJ,综合惊艳', value: 'flex', icon: 'icon-Flex-zonghehuitu'},
    {label: modelMappingLabel.qiHua, tip: '支持中文输入', value: 'qiHua', icon: 'icon-qihua'},
    // {label: '室内家具模型', tip: '效果堪比MJ,综合惊艳', value: 'furniture'},
]
export const resolutionList = [
    {label: '16:9', width: '1920', height: '1080', gptSize: '1024x576', value: '16:9', icon: 'icon-crop--', modal:'flex,qiHua'},
    {label: '3:2', width: '1536', height: '1024', gptSize: '1536x1024', value: '3:2', icon: 'icon-crop--', modal:'gpt-4o-image'},
    {label: '1:1', width: '1024', height: '1024', gptSize: '1024x1024', value: '1:1', icon: 'icon-list-choice-', modal:'gpt-4o-image,flex,qiHua'},
    {label: '2:3', width: '1024', height: '1536', gptSize: '1024x1536', value: '2:3', icon: 'icon-a-16bi9', modal:'gpt-4o-image'},
    {label: '3:4', width: '900', height: '1200', gptSize: '1024x1280', value: '3:4', icon: 'icon-a-3bi4', modal:'flex,qiHua'},
    {label: '9:16', width: '1080', height: '1920', gptSize: '576x1024', value: '9:16', icon: 'icon-a-16bi9', modal:'flex,qiHua'},
]
export const generatorList = [
    {label: '1张', value: '1', icon: 'icon-a-ziyuan211'},
    {label: '2张', value: '2', icon: 'icon-a-ziyuan211'},
    {label: '3张', value: '3', icon: 'icon-a-ziyuan211'},
    {label: '4张', value: '4', icon: 'icon-a-ziyuan211'},
    // { label: '5张', value: '5',icon:'icon-a-ziyuan211'},
]
export const deductionRules = {
    default: {
        flex: 3,
        'flux_kontext_pro_2': 3,
        'flux_kontext_pro_1': 3,
        'ai_product': 15,
        'gpt-4o-image': 20,
        'qiHua':5,
        'video':0,
    },
    vip: {
        flex: 0,
        'flux_kontext_pro_2': 3,
        'flux_kontext_pro_1': 3,
        ai_product: 0,
        'gpt-4o-image': 20,
        'qiHua': 5,
        'video':0,
    }
}
export const httpIndex =  'qihuaimage'