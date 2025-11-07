plugins {
    id("java")
    id("org.jetbrains.intellij") version "1.17.0"
}

group = "com.anthropic"
version = "1.0.0"

repositories {
    mavenCentral()
}

intellij {
    version.set("2023.1.1")
    type.set("IC")
    plugins.set(listOf())
}

dependencies {
    implementation("com.google.code.gson:gson:2.10.1")
}

tasks {
    withType<JavaCompile> {
        sourceCompatibility = "11"
        targetCompatibility = "11"
    }

    patchPluginXml {
        changeNotes.set("""
            <b>1.0.0</b>
            <ul>
                <li>Initial release</li>
                <li>Semantic code search with RAG strategies</li>
                <li>Multi-language support (Python, JavaScript, Java, Go)</li>
                <li>Tool window for search results</li>
                <li>Settings configuration</li>
            </ul>
        """.trimIndent())
    }

    signPlugin {
        certificateChain.set(System.getenv("CERTIFICATE_CHAIN"))
        privateKey.set(System.getenv("PRIVATE_KEY"))
        password.set(System.getenv("PRIVATE_KEY_PASSWORD"))
    }

    publishPlugin {
        token.set(System.getenv("PUBLISH_TOKEN"))
    }
}
