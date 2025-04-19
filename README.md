# 1688-Decryptor

淘宝1688请求数据接口参数逆向

## 参数说明

1688接口请求参数大概如下所示：

请求接口主要修改的就三个参数 `t`、`sign`、`data`

```
{
  "jsv": "2.7.0",
  "appKey": "12574478",
  "t": "1720671061812",
  "sign": "cc8ec6e8ce6ea7a1bd2a4752d4de737a",
  "api": "mtop.alibaba.alisite.cbu.server.pc.ModuleAsyncService",
  "v": "1.0",
  "type": "jsonp",
  "valueType": "string",
  "dataType": "jsonp",
  "timeout": "10000",
  "callback": "mtopjsonp2",
  "data": "{\"componentKey\":\"wp_pc_shop_basic_info\",\"params\":\"{\\\"memberId\\\":\\\"b2b-22133374292418351a\\\"}\"}"
}
```

说明：

1.`t` 是毫秒级时间戳，13位数。

2.`sign` 是几乎所有1688加密的接口用到的参数，会配合cookie进行鉴权。

3.`data` 是 请求参数中的data字段值。

4.`tb_token` 除了sign，有部分接口使用的是_tb_token_参数，在某个接口响应的set-cookie可以得到的。

&emsp;

## 生成sign方法

sign参数值生成需要4个参数，分别是_m_h5_tk、毫秒时间戳、app_key、请求接口时的data参数数据，注意请求接口时t参数就是用来生成sign值的时间戳，sign和t必须对应，否则鉴权失败。如果登录后才能看的数据，那么请求头中必须包含登录后的cookie，否则有sign值也无法请求到数据。

#### 1.如果是使用JS生成，那么直接用node.js执行sign.js文件中的sign函数即可

```
var pre_sign_str = '5655b7041ca049730330701082886efd&1719411639403&12574478&{"componentKey":"wp_pc_shop_basic_info","params":"{\\"memberId\\":\\"b2b-22133374292418351a\\"}"}'
var sign_str =sign(pre_sign_str)
console.log(sign_str)
```

解释一下上面传入的 pre_sign_str 参数：

```
字段一：5655b7041ca049730330701082886efd
说明: _m_h5_tk的前半段部分，存在于cookie中，也可以使用接口生成，_m_h5_tk值一般如 5655b7041ca049730330701082886efd_1720690129578

字段二：1719411639403
说明： 毫秒时间戳

字段三：12574478
说明： appkey 可以固定使用这个值

字段四：{"componentKey":"wp_pc_shop_basic_info","params":"{\\"memberId\\":\\"b2b-22133374292418351a\\"}"}
说明：请求接口data参数值，注意要用\转义
```

#### 2.如果是Python生成，可以使用PyExecJS库执行JS代码（需要node.js环境）

```
import execjs
APP_KEY = '12574478'
_m_h5_tk = ''
data = ''
current_timestamp = get_milliseconds_timestamp()
pre_sign_str = f'{_m_h5_tk.split("_")[0]}&{current_timestamp}&{APP_KEY}&' + data
sign_js_path = './sign.js'
sign = execjs.compile(open(sign_js_path).read()).call('sign', pre_sign_str)
```

**注意，生成的sign用来请求接口时，请求头的cookie中也需要使用相同的 _m_h5_tk 值，否则鉴权失败。具体使用可参考本仓库示例代码。**

#### 3.sign值实际是通过pre_sign_str进行md5加密后得到的，直接对其加密即可



&emsp;

## 运行示例代码

进入仓库项目文件夹，安装依赖

```
pip install -r requirements.txt
```

运行

```
python app.py
```

&emsp;

## 法律声明

**重要**：本项目仅供学习和研究使用。使用本项目进行任何形式的非法活动，包括但不限于侵犯版权、违反服务条款、未经授权访问或修改数据等，均与本项目维护者无关。

- **版权声明**：本项目尊重所有平台的版权和知识产权。请确保在使用本工具时遵守相关法律法规和平台的使用条款。
- **责任限制**：本项目不对因使用本工具而导致的任何直接、间接、特殊或后果性损害承担责任。
- **合规使用**：在使用本项目进行任何操作之前，请确保您的行为符合当地法律法规和平台政策。



---

如果你有任何问题或建议，请在 [Issues](https://github.com/ihmily/1688-Decryptor/issues) 中提出。