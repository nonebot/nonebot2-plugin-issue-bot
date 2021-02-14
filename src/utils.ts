/**插件所需要的信息 */
export interface PluginInfo {
  /**import id */
  id: string
  /**pip地址 */
  link: string
  /**你的插件名称 */
  name: string
  /**简短描述插件功能 */
  desc: string
  /**开发者 */
  author: string
  /**插件项目仓库/主页链接 */
  repo: string
}

/**从议题内容提取插件信息 */
export function extractPluginInfo(body: string, author: string): PluginInfo {
  const idRegexp = /\*\*插件 import 使用的名称\*\*[\n\r]+([^*\n\r]+)/
  const linkRegexp = /\*\*插件 install 使用的名称\*\*[\n\r]+([^*\n\r]+)/
  const descRegexp = /\*\*简短描述插件功能：\*\*[\n\r]+([^*\n\r]+)/
  const nameRegexp = /\*\*你的插件名称：\*\*[\n\r]+([^*\n\r]+)/
  const repoRegexp = /\*\*插件项目仓库\/主页链接\*\*[\n\r]+([^*\n\r]+)/

  const idMatch = body.match(idRegexp)
  const id = idMatch ? idMatch[1] : null
  const linkMatch = body.match(linkRegexp)
  const link = linkMatch ? linkMatch[1] : null
  const descMatch = body.match(descRegexp)
  const desc = descMatch ? descMatch[1] : null
  const nameMatch = body.match(nameRegexp)
  const name = nameMatch ? nameMatch[1] : null
  const repoMatch = body.match(repoRegexp)
  const repo = repoMatch ? repoMatch[1] : null

  if (id && link && desc && name && repo) {
    return {
      id,
      link,
      author,
      desc,
      name,
      repo
    }
  }
  throw new Error('无法匹配成功')
}
