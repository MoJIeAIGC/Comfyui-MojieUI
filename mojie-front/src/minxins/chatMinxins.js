import {getTranslateToEn, useImageDetailRefinement, replaceProductImage,imageInternal,imageInternalRemoval} from "@/api/product.js";
import {isHttp} from "@/utils/utils.js";
import {modelMappingLabel} from "@/options/model.js";
import {useUserStore} from "@/store/userStore.js";
const userStore = useUserStore();
export  function useSubmit () {
    const getKey = (key) => {
        let flexLabel =  modelMappingLabel.flex
        const obj = {
            'ai_product': '迁移替换',
            'multi_image': flexLabel,
            'clue_image': flexLabel,
            'ai_image': flexLabel,
            'ai_text': flexLabel,
            'white':flexLabel,
            'clue':flexLabel,
            'flux_kontext_pro_2':  flexLabel,
            'flux_kontext_pro_1': modelMappingLabel.qiHua,
            'complete_redrawing':  flexLabel,
            'wide_picture': '智能扩图',
            'fine_detail': '局部重绘',
            'internal_supplementation': '内补消除',
            'internal_supplementation_and_removal': '内补消除',
            '色彩调节模型': '色彩调节'
        }
        if (obj[key]) return obj[key];
        if (key && (key.indexOf('gpt') !== -1 || key.indexOf('GPT') !== -1)) {
            return modelMappingLabel.gptLabel
        }
        if (key && (key.indexOf('gemini') !== -1)) {
            return 'Gemini-image'
        }
        if (key && (key.indexOf('flex') !== -1 || key.indexOf('ai_') !== -1)) {
            return flexLabel
        }
        if (key && (key.indexOf('volcengine') !== -1)) {
            return modelMappingLabel.qiHua
        }
        return '未知'
    }
    const hasEndBtn = (item) => {
        //除失败以外的需要添加文本的api
        let status = getStatus(item)
        if(status === 'failed') return false;
        const noEdtModel = ['wide_picture','色彩调节模型','internal_supplementation_and_removal']
        return !noEdtModel.includes(item.model_used)
    }
    const getStatus = (item) => {
        if (item.task_info && item.task_info.status ) {
            return  item.task_info.status
        }
        return item.status
    }
    const initItemToArray = (item) => {
        let str = item.image_list
        let _list = [], maskList = []
        if (item.model_used === 'ai_product') {
            if (item.task_info && item.task_info.input_data && item.task_info.input_data.metadata && item.task_info.input_data.metadata.add_new_data) {
                let obj = JSON.parse(item.task_info.input_data.metadata.add_new_data);
                if (obj.url) _list = [obj.url]
            }
            // if(item.task_info&&item.task_info.input_data&&item.task_info.input_data.mask_url) {
            //   maskList = [item.task_info.input_data.mask_url]
            // }
        }
        // if(item.task_info&&item.task_info.input_data&&item.task_info.input_data.mask_url) {
        //   maskList = [item.task_info.input_data.mask_url]
        // }
        //const arrayStr = 'pending,failed,completed'
        if (!str || str === 'pending') return _list.concat(maskList)
        if (!isHttp(str)) return []
        if (Array.isArray(str)) return _list.concat(str).concat(maskList)
        return _list.concat(str.split(',')).concat(maskList)
    }
    //当前对话项编辑再发消耗积分
    const getPoints = (item,_Rules) => {
        let _modelType = 'flex',number =1,_list = initItemToArray(item)
        if(item.task_info && item.task_info.input_data && item.task_info.input_data.batch_size ) number = item.task_info.input_data.batch_size
        const key = item.model_used
        if (key && (key.indexOf('gpt') !== -1 || key.indexOf('GPT') !== -1)) _modelType = 'gpt-4o-image'
        if (key&&(key.indexOf('volcengine')!==-1||key.indexOf('dou')!==-1)) _modelType =  'qiHua'
        let points = _modelType === 'gpt-4o-image' ? _Rules['gpt-4o-image'] : _Rules['flex']
        if (_modelType === 'flex') {
            points = points * parseInt(number)
            if(_list.length > 0) {
                points =  _Rules['flux_kontext_pro_2']
            }
        }
        if (_modelType === 'qiHua') {
            if(_list.length > 0) {
                points =_Rules['flux_kontext_pro_1']
            } else {
                points = _Rules['qiHua']
            }
        }
        if(key&&key ==='ai_product')   points = _Rules['ai_product']
        const isVip = userStore.vipInfo&&userStore.vipInfo.level
        console.log(points)
        if (isVip && points ===0) return '会员免费'
        return  points +'算力'
    }
    //产品替换
    const replaceSubmit = async (item) => {
        if (_data.generate['text']) {
            let _res = await getTranslateToEn(_data.generate['text'])
            if (_res.data && _res.data.translated_text) _data.generateEn['text'] = _res.data.translated_text
        }
        let text = 'This is a collage picture，in the left Objects replaces the Objects in the right picture,'
        if (_data.generate.text) text = text + _data.generateEn.text
        replaceProductImage({
            conversation_id: !props.chatId || props.chatId === -1 || props.chatId === '-1' ? '' : props.chatId,
            //description: 'the left image is a subject,the subject on the right image',

            add_new_data: JSON.stringify({
                text: _data.generate.text,
                templateText: _data.generate.templateText,
                url: _data.pro.image_url,
                type: 'product_replacement'
            }),
            description: text,
            level: _data.generate.strength,
            white_url: _data.whiteImage.image_url,
            template_url: _data.replace.image_url,
            mask_url: _data.maskImage.image_url
        }).then(res => {

        }).finally(() => {
            _data.timer2 = setTimeout(() => {
                _data.loading = false
            }, 15 * 1000)
        })
    }
    //内补
    const internalSubmit = async () => {
        _data.textEn = ''
        if(_data.text&&tabIndex.value==='1'){
            let _res = await getTranslateToEn(_data.text)
            if(_res.data&&_res.data.translated_text) _data.textEn = _res.data.translated_text
        }
        const sub_data = {
            conversation_id:_data.sessionIdx,
            description: _data.textEn|| _data.text,
            add_new_data:JSON.stringify({
                text:_data.text,
                type:'eliminate',
            }),
            url: _data.image.image_url,
            mask_url: _data.maskImage.image_url
        }
        imageInternal(sub_data).then((res) => {

        }).finally(()=>{

        })
    }
    //消除
    const removalSubmit = async (item) => {
        const sub_data = {
            conversation_id:_data.sessionIdx,
            description: 'Remove here',
            add_new_data:JSON.stringify({
                text:"",
                type:'eliminate',
            }),
            url: _data.image.image_url,
            mask_url: _data.maskImage.image_url
        }
        imageInternalRemoval(sub_data).then((res) => {
            emit('change', {type:'eliminate', sendInfo: {
                    description: "string",
                    url: _data.image.image_url,
                    mask_url: _data.maskImage.image_url
                },res: res.data},res.data.conversation_id)
        }).finally(()=>{

        })
    }
    //精修
    const refineSubmit = async (item) => {
        if (_data.generate['text']) {
            let _res = await getTranslateToEn(_data.generate['text'])
            if (_res.data && _res.data.translated_text) _data.generateEn['text'] = _res.data.translated_text
        }
        useImageDetailRefinement(
            {
                conversation_id: !props.chatId || props.chatId === -1 || props.chatId === '-1' ? '' : props.chatId,
                description: _data.textEn || _data.text || 'refine',
                add_new_data: JSON.stringify({text: _data.text || '精修', type: 'refine'}),
                level: _data.strength,
                url: _data.image.image_url,
                mask_url: _data.maskImage.image_url
            }
        ).then(res => {

        }).finally(res => {

        })
    }
    return {refineSubmit, replaceSubmit,internalSubmit,removalSubmit,getPoints,initItemToArray,getStatus,hasEndBtn,getKey}
}