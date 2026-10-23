//! 界面资源适配：把网络验证码图片校验后转成 WebView 可直接显示的 data URL。
//!
//! 轨迹绘制已移到前端（SVG），随 MD3 主题实时着色；这里只保留图片边界检查，
//! 避免未经解码验证的网络字节直接进入界面。

use base64::{engine::general_purpose::STANDARD, Engine as _};

pub fn captcha_data_url(bytes: &[u8]) -> Result<String, String> {
    let format = image::guess_format(bytes)
        .map_err(|_| "验证码接口未返回有效图片，请刷新重试".to_string())?;
    // 复用 api 层的尺寸/内存上限校验，校验通过后再交给 WebView。
    crate::api::decode_captcha(bytes)?;
    let mime = match format {
        image::ImageFormat::Png => "image/png",
        image::ImageFormat::Jpeg => "image/jpeg",
        image::ImageFormat::Gif => "image/gif",
        image::ImageFormat::WebP => "image/webp",
        _ => return Err("验证码图片格式不受支持，请刷新重试".into()),
    };
    Ok(format!("data:{mime};base64,{}", STANDARD.encode(bytes)))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn captcha_decoding_is_bounded_and_rejects_junk() {
        let oversized = image::DynamicImage::ImageRgb8(image::RgbImage::new(4_000, 8));
        let mut buffer = std::io::Cursor::new(Vec::new());
        oversized
            .write_to(&mut buffer, image::ImageFormat::Png)
            .unwrap();
        assert!(captcha_data_url(&buffer.into_inner()).is_err());
        assert!(captcha_data_url(b"not an image").is_err());
    }

    #[test]
    fn valid_captcha_is_returned_as_data_url() {
        let mut buffer = std::io::Cursor::new(Vec::new());
        image::DynamicImage::ImageRgb8(image::RgbImage::new(110, 40))
            .write_to(&mut buffer, image::ImageFormat::Png)
            .unwrap();
        let url = captcha_data_url(&buffer.into_inner()).unwrap();
        assert!(url.starts_with("data:image/png;base64,"));
    }
}
