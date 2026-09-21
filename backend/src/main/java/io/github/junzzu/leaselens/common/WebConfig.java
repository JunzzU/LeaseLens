package io.github.junzzu.leaselens.common;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.info.License;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
public class WebConfig implements WebMvcConfigurer {

    private final String[] allowedOrigins;

    public WebConfig(@Value("${leaselens.cors.allowed-origins}") String[] allowedOrigins) {
        this.allowedOrigins = allowedOrigins;
    }

    /** Browsers need CORS for the website; native app clients don't send Origin and aren't affected. */
    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/api/**").allowedOrigins(allowedOrigins).allowedMethods("GET");
    }

    @Bean
    OpenAPI openApi() {
        return new OpenAPI().info(new Info()
                .title("LeaseLens Toronto API")
                .version("v1")
                .description("Public records about Toronto rental apartment buildings: RentSafeTO registration and "
                        + "evaluations. Contains information licensed under the Open Government Licence – Toronto. "
                        + "LeaseLens Toronto is independent and not affiliated with or endorsed by the City of Toronto.")
                .license(new License().name("Data: Open Government Licence – Toronto")
                        .url("https://open.toronto.ca/open-data-license/")));
    }
}
